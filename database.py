from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from config import config

SQLALCHEMY_DATABASE_URL = config.DATABASE_URL
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# 2. 创建异步会话工厂（这就是你说的工厂）
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # 记住这个参数，老手都会加
)

# 3. 定义基类（用来建表的）
Base = declarative_base()

# 4. 最重要的依赖注入函数（FastAPI每次请求用它拿会话）
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

class Book(Base):
    __tablename__ = "books"  # 表名

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False, comment="书名")
    author = Column(String(50), nullable=False, comment="作者")
    created_at = Column(DateTime, default=datetime.now)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)