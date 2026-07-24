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

config = Config()
