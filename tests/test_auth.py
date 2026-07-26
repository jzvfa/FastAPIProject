"""
认证相关接口测试

怎么跑（项目根目录、已启动本机 MySQL）：

    python -m pytest tests/test_auth.py -v
"""
import uuid


def _unique_username() -> str:
    # 每次用不重复的用户名，避免和数据库里已有用户撞车
    return f"test_{uuid.uuid4().hex[:8]}"


def test_register_success(client):
    username = _unique_username()
    resp = client.post(
        "/auth/register",
        json={"username": username, "password": "test1234"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert data["data"]["username"] == username


def test_register_duplicate_username(client):
    username = _unique_username()
    payload = {"username": username, "password": "test1234"}

    first = client.post("/auth/register", json=payload)
    assert first.status_code == 200

    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400
    assert "注册" in second.json()["msg"] or "用户名" in second.json()["msg"]


def test_login_success(client):
    username = _unique_username()
    password = "test1234"

    reg = client.post(
        "/auth/register",
        json={"username": username, "password": password},
    )
    assert reg.status_code == 200

    # OAuth2 登录接口要的是表单，不是 JSON
    resp = client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    username = _unique_username()
    client.post(
        "/auth/register",
        json={"username": username, "password": "test1234"},
    )

    resp = client.post(
        "/auth/login",
        data={"username": username, "password": "wrong-password"},
    )
    assert resp.status_code == 401
