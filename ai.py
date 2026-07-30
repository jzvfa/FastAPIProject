# ai.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from auth import get_current_user
from database import User
from config import config

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


SYSTEM_PROMPT = """你是一个专业的图书推荐助手。
你的职责是只回答与书籍、阅读、文学、作者、图书推荐相关的问题。
如果用户问的问题与书籍无关，请礼貌地拒绝回答，并引导用户询问书籍相关的问题。
你可以结合当前会话里已经聊过的内容继续回答。"""

checkpointer = InMemorySaver()

agent = create_agent(
    model=llm,
    tools=[],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    question = (request.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    messages = [{"role": "user", "content": question}]
    config_run = {"configurable": {"thread_id": str(current_user.id)}}
    try:
        result = agent.invoke({"messages": messages}, config=config_run)
        answer = result["messages"][-1].content
        return ChatResponse(answer=answer, thread_id=str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 服务调用失败: {str(e)}")
