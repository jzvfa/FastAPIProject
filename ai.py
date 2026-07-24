# ai.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from config import config

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


# 初始化大模型（从 config 读取配置）
llm = ChatOpenAI(
    model=config.LLM_MODEL,
    api_key=config.API_KEY,
    base_url=config.BASE_URL,
    temperature=0.7,
    timeout=120,
    max_retries=2,
)

# 系统提示词：限定只能回答书籍相关问题
SYSTEM_PROMPT = """你是一个专业的图书推荐助手。
你的职责是只回答与书籍、阅读、文学、作者、图书推荐相关的问题。
如果用户问的问题与书籍无关，请礼貌地拒绝回答，并引导用户询问书籍相关的问题。"""


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=request.question),
        ]
        response = llm.invoke(messages)
        return ChatResponse(answer=response.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 服务调用失败: {str(e)}")
