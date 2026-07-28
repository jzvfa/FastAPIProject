"""
测试共用夹具（fixture）

TestClient：不真的开浏览器，直接在进程里模拟 HTTP 请求打你的 FastAPI。
"""
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client():
    """整个测试会话共用一个 client，避免反复 startup 连库不稳定。"""
    with TestClient(app) as c:
        yield c
