from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from starlette.exceptions import HTTPException as StarletteHTTPException

from database import engine, Base, get_db, Book, User
from redis_client import redis_client, get_cache, set_cache
from auth import router as auth_router, get_current_user

from loguru import logger
import sys

from ai import router as ai_router

# ---------- 日志配置 ----------
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{file}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/app.log",
    rotation="100 MB",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}"
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(ai_router)

FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


# ---------- 统一响应辅助函数 ----------
def success_response(data=None, msg="success"):
    return {"code": 200, "msg": msg, "data": data}


def error_response(code: int, msg: str):
    return {"code": code, "msg": msg, "data": None}


# ---------- 全局异常处理器 ----------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.status_code, exc.detail)
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content=error_response(422, "参数校验失败")
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content=error_response(500, "服务器内部错误，请稍后重试")
    )


# ---------- 启动事件 ----------
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表检查/创建完成！")


# ---------- 图书 CRUD ----------
class BookCreate(BaseModel):
    title: str
    author: str


class BookUpdate(BaseModel):
    title: str
    author: str


@app.post("/books/")
async def create_book(
    book: BookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not book.title or not book.author:
        raise HTTPException(status_code=400, detail="标题和作者不能为空")
    new_book = Book(title=book.title, author=book.author, user_id=current_user.id)
    db.add(new_book)
    await db.commit()
    await db.refresh(new_book)
    return success_response(data=new_book, msg="添加成功")


@app.get("/books/{book_id}")
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    cache_key = f"book:{book_id}"
    cached_book = await get_cache(cache_key)
    if cached_book:
        logger.info(f"✅ 命中了 Redis 缓存: {cache_key}")
        return success_response(data=cached_book)

    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")

    book_dict = {"id": book.id, "title": book.title, "author": book.author}
    await set_cache(cache_key, book_dict, expire=60)
    logger.info(f"🔄 从 MySQL 查询，并写入 Redis: {cache_key}")
    return success_response(data=book_dict)


@app.put("/books/{book_id}")
async def update_book(
    book_id: int,
    book_update: BookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if book.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作")
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")

    book.title = book_update.title
    book.author = book_update.author
    await db.commit()
    await db.refresh(book)

    cache_key = f"book:{book_id}"
    await redis_client.delete(cache_key)
    logger.info(f"🗑️ 已删除 Redis 缓存: {cache_key}")
    return success_response(data=book, msg="更新成功")


@app.delete("/books/{book_id}")
async def delete_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if book.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作")
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")

    await db.delete(book)
    await db.commit()

    cache_key = f"book:{book_id}"
    deleted_count = await redis_client.delete(cache_key)
    if deleted_count:
        logger.info(f"🗑️ 已删除 Redis 缓存: {cache_key}")
    else:
        logger.info(f"ℹ️ Redis 中无此缓存: {cache_key}")
    return success_response(msg=f"图书 ID {book_id} 已删除")


@app.get("/books/")
async def get_books(
        page: int = Query(default=1, ge=1, description="当前页码"),
        page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
        keyword: str | None = Query(default=None, description="书名或作者关键词"),
        db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * page_size

    stmt = select(Book)
    if keyword:
        stmt = stmt.where(
            Book.title.ilike(f"%{keyword}%") | Book.author.ilike(f"%{keyword}%")
        )

    count_stmt = select(func.count(Book.id))
    if keyword:
        count_stmt = count_stmt.where(
            Book.title.ilike(f"%{keyword}%") | Book.author.ilike(f"%{keyword}%")
        )
    total = await db.scalar(count_stmt)

    stmt = stmt.offset(skip).limit(page_size)
    result = await db.execute(stmt)
    books = result.scalars().all()

    books_data = [
        {"id": book.id, "title": book.title, "author": book.author}
        for book in books
    ]

    return success_response(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": books_data
    })