"""
图书 CRUD 接口测试（写操作需要登录 Token）

怎么跑（需本机 MySQL；Redis 可不开启）：
    .\\.venv\\Scripts\\python.exe -m pytest tests/test_books.py -v
"""
import uuid

import pytest


def _unique_title() -> str:
    return f"pytest书_{uuid.uuid4().hex[:8]}"


def _unique_username() -> str:
    return f"book_user_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def auth_headers(client):
    """注册并登录，返回带 Bearer Token 的请求头。"""
    username = _unique_username()
    password = "test1234"
    reg = client.post(
        "/auth/register",
        json={"username": username, "password": password},
    )
    assert reg.status_code == 200

    login = client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_book(
    client, auth_headers, title: str, author: str = "测试作者", quantity: int = 1
) -> dict:
    """创建一本书，返回 data（含 id/title/author/quantity）。"""
    resp = client.post(
        "/books/",
        json={"title": title, "author": author, "quantity": quantity},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["title"] == title
    assert body["data"]["author"] == author
    assert body["data"]["quantity"] == quantity
    assert "id" in body["data"]
    return body["data"]


def test_create_book_unauthorized(client):
    """没 Token 不能创建。"""
    resp = client.post(
        "/books/",
        json={"title": _unique_title(), "author": "测试作者", "quantity": 1},
    )
    assert resp.status_code == 401


def test_create_book(client, auth_headers):
    title = _unique_title()
    author = "测试作者"

    resp = client.post(
        "/books/",
        json={"title": title, "author": author, "quantity": 3},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["title"] == title
    assert body["data"]["author"] == author
    assert body["data"]["quantity"] == 3


def test_list_books(client, auth_headers):
    """列表分页，并返回数量。"""
    title = _unique_title()
    _create_book(client, auth_headers, title=title, author="作者B", quantity=5)

    resp = client.get(
        "/books/",
        params={"page": 1, "page_size": 10},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "items" in body["data"]
    assert "total" in body["data"]
    assert body["data"]["total"] >= 1
    matched = [item for item in body["data"]["items"] if item["title"] == title]
    assert matched
    assert matched[0]["quantity"] == 5
    assert matched[0]["author"] == "作者B"


def test_list_books_like(client, auth_headers):
    """模糊查询 /books/like，返回格式与列表一致。"""
    title = _unique_title()
    _create_book(client, auth_headers, title=title, author="模糊作者", quantity=2)

    resp = client.get(
        "/books/like",
        params={"keyword": title[:8]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "items" in body["data"]
    titles = [item["title"] for item in body["data"]["items"]]
    assert title in titles


def test_update_book(client, auth_headers):
    title = _unique_title()
    book = _create_book(client, auth_headers, title=title, author="旧作者", quantity=1)
    book_id = book["id"]

    new_title = f"{title}_已更新"
    new_author = "新作者"
    resp = client.put(
        f"/books/{book_id}",
        json={"title": new_title, "author": new_author, "quantity": 8},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["id"] == book_id
    assert body["data"]["title"] == new_title
    assert body["data"]["author"] == new_author
    assert body["data"]["quantity"] == 8


def test_delete_book(client, auth_headers):
    title = _unique_title()
    book = _create_book(client, auth_headers, title=title, author="待删作者")
    book_id = book["id"]

    del_resp = client.delete(f"/books/{book_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["code"] == 200

    list_resp = client.get(
        "/books/",
        params={"page": 1, "page_size": 100},
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    titles = [item["title"] for item in list_resp.json()["data"]["items"]]
    assert title not in titles
