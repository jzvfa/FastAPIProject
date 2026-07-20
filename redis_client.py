import json
from redis.asyncio import Redis

# 创建异步 Redis 客户端（连接本地默认端口）
from config import config
redis_client = Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    decode_responses=True,
    protocol=2
)

# 工具函数：从 Redis 取数据（自动反序列化 JSON）
async def get_cache(key: str):
    data = await redis_client.get(key)
    if data:
        return json.loads(data)  # 把字符串转回 Python 字典/对象
    return None

# 工具函数：存数据到 Redis（自动序列化 JSON），并设置过期时间（秒）
async def set_cache(key: str, value, expire: int = 60):
    await redis_client.setex(key, expire, json.dumps(value))