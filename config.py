import os
from dotenv import load_dotenv

load_dotenv()

class Config:

    DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))

    CACHE_EXPIRE = int(os.getenv("CACHE_EXPIRE", 60))
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    API_KEY=os.getenv("API_KEY")
    BASE_URL = os.getenv("BASE_URL")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

    # RAG embedding（可与对话使用不同服务商；未配置时回退到对话的 Key/URL）
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY") or API_KEY
    EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL") or BASE_URL
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


config = Config()
