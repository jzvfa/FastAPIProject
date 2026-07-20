import asyncio
from redis_client import redis_client

async def test():
    try:
        # 向 Redis 写入一个测试键
        await redis_client.set("test_key", "Hello from Windows!")
        # 读取它
        result = await redis_client.get("test_key")
        print(f"✅ Redis 连接成功！读取到数据: {result}")
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")

asyncio.run(test())