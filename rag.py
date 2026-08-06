"""
馆藏 RAG 模块（FAISS）

流程：
1. 从 MySQL 读取 Book
2. 拼成短文本（一书一段，暂不切分）
3. embedding → 写入 FAISS，保存到 data/faiss_books/
4. search_books(问题) → 返回最相关的若干段原文

下一步由你在 ai.py 里调用 search_books，把结果拼进 prompt 或做成 Tool。
"""
from __future__ import annotations

from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from loguru import logger
from sqlalchemy import select

from config import config
from database import AsyncSessionLocal, Book

INDEX_PATH = Path("data/faiss_books")

embeddings = OpenAIEmbeddings(
    model=config.EMBEDDING_MODEL,
    api_key=config.EMBEDDING_API_KEY,
    base_url=config.EMBEDDING_BASE_URL,
)

async def add_books_to_faiss():
    async with AsyncSessionLocal() as db:
        result=await db.execute(select(Book))
        books = list(result.scalars().all())
        return books

async def add_book_to_faiss(books: list[Book]):
    docs = [
    Document(page_content=f"书名：{b.title} 作者：{b.author} 库存：{b.quantity}")
    for b in books
]
    INDEX_PATH.mkdir(parents=True, exist_ok=True)

    if not docs:
        return

    db_faiss = FAISS.from_documents(docs, embeddings)
    db_faiss.save_local(str(INDEX_PATH))

async def add_book():
    books = await add_books_to_faiss()
    await add_book_to_faiss(books)


async def refresh_catalog_index() -> None:
    """馆藏增删改成功后调用：重建 FAISS。失败不抛出，避免拖垮主业务。"""
    try:
        await add_book()
    except Exception:
        logger.exception("重建馆藏索引失败")


def search_books(query: str, k: int = 3) -> list[str]:
    db_faiss = FAISS.load_local(
        str(INDEX_PATH),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    hits = db_faiss.similarity_search(query, k=k)
    return [doc.page_content for doc in hits]