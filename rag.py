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
from sqlalchemy import select

from config import config
from database import AsyncSessionLocal, Book

INDEX_PATH = Path("data/faiss_books")

embeddings = OpenAIEmbeddings(
    model=config.LLM_MODEL,
    api_key=config.API_KEY,
    base_url=config.BASE_URL,
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
    
    if INDEX_PATH.exists():
        db_faiss = FAISS.load_local(INDEX_PATH, embeddings)
        db_faiss.add_documents(docs)
        db_faiss.save_local(INDEX_PATH)
    else:
        db_faiss = FAISS.from_documents(docs, embeddings)
        db_faiss.save_local(INDEX_PATH)


