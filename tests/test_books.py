"""
图书 CRUD 接口测试

套路：先创建 → 断言 → 再测查/改/删

怎么跑（需本机 MySQL；Redis 可不开启，测试里已 mock）：
    .\\.venv\\Scripts\\python.exe -m pytest tests/test_books.py -v
"""
import uuid

import pytest


def _unique_title() -> str:
    return f"pytest书_{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """图书接口会碰 Redis；测试里改成空操作，避免本机没开 Redis 就失败。"""

    async def fake_get_cache(key: str):
        return None

    async def fake_set_cache(key: str, value, expire: int = 60):
        return None

    async def fake_delete(*args, **kwargs):
        return 0

    monkeypatch.setattr("main.get_cache", fake_get_cache)
    monkeypatch.setattr("main.set_cache", fake_set_cache)
    monkeypatch.setattr("main.redis_client.delete", fake_delete)


def _create_book(client, title: str, author: str = "测试作者") -> dict:
    """创建一本书，返回 data（含 id/title/author）。"""
    resp = client.post("/books/", json={"title": title, "author": author})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["title"] == title
    assert body["data"]["author"] == author
    assert "id" in body["data"]
    return body["data"]


def test_create_book(client):
    title = _unique_title()
    author = "测试作者"

    resp = client.post(
        "/books/",
        json={"title": title, "author": author},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["title"] == title
    assert body["data"]["author"] == author


def test_get_book(client):
    title = _unique_title()
    book = _create_book(client, title=title, author="作者A")
    book_id = book["id"]

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["id"] == book_id
    assert body["data"]["title"] == title
    assert body["data"]["author"] == "作者A"


def test_list_books(client):
    title = _unique_title()
    _create_book(client, title=title, author="作者B")

    # 用 keyword 精确搜，避免列表第一页没有这本新书
    resp = client.get(
        "/books/",
        params={"page": 1, "page_size": 10, "keyword": title},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "items" in body["data"]
    assert "total" in body["data"]
    assert body["data"]["total"] >= 1
    titles = [item["title"] for item in body["data"]["items"]]
    assert title in titles


def test_update_book(client):
    title = _unique_title()
    book = _create_book(client, title=title, author="旧作者")
    book_id = book["id"]

    new_title = f"{title}_已更新"
    new_author = "新作者"
    resp = client.put(
        f"/books/{book_id}",
        json={"title": new_title, "author": new_author},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["id"] == book_id
    assert body["data"]["title"] == new_title
    assert body["data"]["author"] == new_author


def test_delete_book(client):
    title = _unique_title()
    book = _create_book(client, title=title, author="待删作者")
    book_id = book["id"]

    del_resp = client.delete(f"/books/{book_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["code"] == 200

    get_resp = client.get(f"/books/{book_id}")
    assert get_resp.status_code == 404
