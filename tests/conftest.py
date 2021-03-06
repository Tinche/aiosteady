from typing import AsyncGenerator
import pytest

from aioredis import create_redis, Redis


@pytest.fixture
async def aioredis() -> AsyncGenerator[Redis, None]:
    res = await create_redis("redis://localhost:6379")
    yield res
    res.close()
    await res.wait_closed()