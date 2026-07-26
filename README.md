# BookShelf（FastAPI 图书管理）

基于 FastAPI 的图书 CRUD 服务，带用户注册/登录、Redis 缓存、AI 图书助手，以及简单前端页面。

## 环境要求

- Python 3.11+
- MySQL 8
- Redis 7
-（可选）Docker / Docker Compose

## 配置

1. 复制环境变量模板：

```bash
copy .env.example .env
```

2. 编辑 `.env`，填入真实值（数据库、`SECRET_KEY`、大模型 `API_KEY` 等）。

**注意：`.env` 含密钥，不要提交到 Git。**

## 本地启动

```bash
# 建议使用项目虚拟环境
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

浏览器打开：http://127.0.0.1:8000/

API 文档：http://127.0.0.1:8000/docs

## Docker 启动（MySQL + Redis + 应用一起）

确保项目目录下已有配置好的 `.env`，然后：

```bash
docker compose up --build
```

同样访问：http://127.0.0.1:8000/

## 运行测试

本机需已配置 `.env`，并且 MySQL 可连接：

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_auth.py -v
```

## 主要接口

| 模块 | 路径 |
|------|------|
| 注册 / 登录 | `POST /auth/register`、`POST /auth/login` |
| 图书 CRUD | `/books/` |
| AI 助手 | `POST /ai/chat` |
