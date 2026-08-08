# ai.py
import json

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import select, update
from auth import get_current_user
from database import User, Book, AsyncSessionLocal
from config import config
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from rag import search_books, refresh_catalog_index

router = APIRouter(prefix="/ai", tags=["ai"])

llm = ChatOpenAI(
        model=config.LLM_MODEL,
        api_key=config.API_KEY,
        base_url=config.BASE_URL,
        temperature=0.7,
        timeout=120,
        max_retries=2,
    )


class ChatRequest(BaseModel):
    question: str


SYSTEM_PROMPT = """你是图书馆的馆藏管理助手，协助管理员维护图书数据。

你可以：
1. 回答与书籍、阅读、作者相关的一般问题；可结合你已有的公开知识介绍书籍与作者（例如录入前了解作者简介、作品背景）；
2. 当管理员要求上架/录入图书时，调用 create_book_tool（需要书名、作者、数量）；
3. 当管理员明确确认要删除/下架某本书时，再调用 delete_book_tool（需要书名）；
4. 当管理员要更新书籍数量时，调用 update_book_tool（需要书名、作者、数量）；
5. 仅当管理员明确要求查「当前库 / 本馆 / 馆藏里 / 库存里」有什么书、或基于现有馆藏做推荐/归纳时，才调用 search_catalog_tool；必须以该工具返回结果为准，不要把馆外图书说成馆藏已有。

注意：
- 普通「推荐几本书」「介绍某作者」→ 不要调用 search_catalog_tool，用公开知识回答即可；回答时若涉及推荐，可说明这些不一定在本馆馆藏中；
- 删除前若管理员尚未确认，先向管理员确认，不要擅自删除；
- 录入、改库存、删除时不要调用 search_catalog_tool；
- 一次处理多本书时，优先在同一轮里合理调用工具，并根据工具返回结果如实汇报；
- 与图书管理无关的问题，请礼貌拒绝并引导回馆藏相关话题；
- 结合当前会话已聊过的内容继续回答。"""

checkpointer = InMemorySaver()

@tool
async def create_book_tool(title:str,author:str,quantity:int,config:RunnableConfig)->str:
    """
    当管理员要上架/录入新书时调用。需要书名、作者和数量。
    """
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        return "权限不足，无法添加书籍"
    created = False
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(select(Book).where(Book.title == title, Book.author == author))
            result = result.scalar_one_or_none()
            if result:
                return f"书籍{title}已存在"
            db.add(Book(title=title, author=author, user_id=user_id,quantity=quantity))
            created = True
    if created:
        await refresh_catalog_index()
    return f"书籍{title}录入成功"

@tool
async def update_book_tool(title:str,author:str,quantity:int,config:RunnableConfig)->str:
    """
    当管理员要更新书籍数量时调用，需要书名和作者
    """
    user_id = config.get("configurable",{}).get("user_id")
    if not user_id:
        return "权限不足，无法更新书籍数量"
    updated = False
    async with AsyncSessionLocal() as db:
        async with db.begin():
            book = await db.execute(select(Book).where(Book.title == title, Book.author == author))
            book = book.scalar_one_or_none()
            if not book:
                return f"书籍{title}不存在"
            await db.execute(update(Book).where(Book.id == book.id).values(quantity=quantity))
            updated = True
    if updated:
        await refresh_catalog_index()
    return f"书籍{title}数量更新成功"

@tool
async def delete_book_tool(title:str,config:RunnableConfig)->str:
    """
    当管理员说要删除/下架书时候调用，需要向管理员确认之后在删除
    """
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        return "权限不足，无法删除书籍"
    deleted = False
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(select(Book).where(Book.title == title))
            result = result.scalar_one_or_none()
            if not result:
                return f"书籍{title}不存在"
            await db.delete(result)
            deleted = True
    if deleted:
        await refresh_catalog_index()
    return f"书籍{title}已删除"

@tool
async def get_book_tool(title: str, author: str, config: RunnableConfig) -> str:
    """
    当管理员要获取书籍数量时调用，需要书名
    """
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        return "权限不足，无法获取书籍数量"
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(select(Book).where(Book.title == title,Book.author == author))
            result = result.scalar_one_or_none()
            if not result:
                return f"书籍{title}不存在"
            else:
                return f"书籍{title}作者为{result.author}数量为{result.quantity}本"

@tool
def search_catalog_tool(query: str) -> str:
    """
    仅当管理员明确要查当前馆藏/本库/库存里的图书，或基于现有馆藏做推荐、归纳时调用。
    普通的泛推荐、作者简介、录入前了解书籍背景时不要调用。
    """
    try:
        hits = search_books(query, k=3)
    except Exception as e:
        return f"馆藏检索失败：{e}（可能尚未建立索引）"
    if not hits:
        return "未检索到相关馆藏"
    return "\n".join(hits)


agent = create_agent(
        model=llm,
        tools=[create_book_tool,delete_book_tool,update_book_tool,get_book_tool,search_catalog_tool],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
            )


@router.post("/chat")
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    question = (request.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    messages = [{"role": "user", "content": question}]
    thread_id = str(current_user.id)
    config_run = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": current_user.id,
        }
    }

    async def event_gen():
        try:
            async for event in agent.astream_events(
                {"messages": messages},
                config=config_run,
                version="v2",
            ):
                if event.get("event") != "on_chat_model_stream":
                    continue
                chunk = event.get("data", {}).get("chunk")
                if chunk is None:
                    continue
                text = chunk.content
                if isinstance(text, str) and text:
                    yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            checkpointer.delete_thread(thread_id)
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
