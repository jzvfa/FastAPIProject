# ai.py
from fastapi import APIRouter, HTTPException, Depends
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


class ChatResponse(BaseModel):
    answer: str
    thread_id: str


SYSTEM_PROMPT = """你是图书馆的馆藏管理助手，协助管理员维护图书数据。

你可以：
1. 回答与书籍、馆藏、阅读相关的问题；
2. 当管理员要求上架/录入图书时，调用 create_book_tool（需要书名、作者、数量）；
3. 当管理员明确确认要删除/下架某本书时，再调用 delete_book_tool（需要书名）；
4. 当管理员要更新书籍数量时，调用 update_book_tool（需要书名、作者、数量）。

注意：
- 删除前若管理员尚未确认，先向管理员确认，不要擅自删除；
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
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(select(Book).where(Book.title == title, Book.author == author))
            result = result.scalar_one_or_none()
            if result:
                return f"书籍{title}已存在"
            else:
                db.add(Book(title=title, author=author, user_id=user_id,quantity=quantity))
                return f"书籍{title}录入成功"

@tool
async def update_book_tool(title:str,author:str,quantity:int,config:RunnableConfig)->str:
    """
    当管理员要更新书籍数量时调用，需要书名和作者
    """
    user_id = config.get("configurable",{}).get("user_id")
    if not user_id:
        return "权限不足，无法更新书籍数量"
    async with AsyncSessionLocal() as db:
        async with db.begin():
            book = await db.execute(select(Book).where(Book.title == title, Book.author == author))
            book = book.scalar_one_or_none()
            if not book:
                return f"书籍{title}不存在"
            result = await db.execute(update(Book).where(Book.id == book.id).values(quantity=quantity))
            return f"书籍{title}数量更新成功"

@tool
async def delete_book_tool(title:str,config:RunnableConfig)->str:
    """
    当管理员说要删除/下架书时候调用，需要向管理员确认之后在删除
    """
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        return "权限不足，无法删除书籍"
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(select(Book).where(Book.title == title))
            result = result.scalar_one_or_none()
            if  not result:
                return f"书籍{title}不存在"
            else:
                await db.delete(result)
                return f"书籍{title}已删除"

agent = create_agent(
        model=llm,
        tools=[create_book_tool,delete_book_tool,update_book_tool],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
            )

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    question = (request.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    messages = [{"role": "user", "content": question}]
    config_run = {
        "configurable": {
            "thread_id": str(current_user.id),
            "user_id": current_user.id,
        }
    }
    try:
        result =await agent.ainvoke({"messages": messages}, config=config_run)
        answer = result["messages"][-1].content
        return ChatResponse(answer=answer, thread_id=str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 服务调用失败: {str(e)}")
