import pytest
from asyncio import sleep

from aioredis import Redis
from aiosteady.leakybucket import Throttler


@pytest.mark.asyncio
async def test_no_block_quick(aioredis: Redis):
    sut = Throttler(aioredis)

    key = "test_key"

    await aioredis.delete(key)
    for i in range(10):
        peek = await sut.peek(key, 10, 5)
        assert peek.success
        assert peek.level == i
        res = await sut.consume(key, 10, 5)
        assert res.success
        assert res.level == i + 1
        assert 4 < res.until_next_drop <= 5
        assert res.blocked_for is None

    peek = await sut.peek(key, 10, 5)
    assert not peek.success
    assert peek.level == 10
    res = await sut.consume(key, 10, 5)
    assert not res.success


@pytest.mark.asyncio
async def test_block(aioredis: Redis):
    sut = Throttler(aioredis)

    key = "test_key"
    block_duration = 1
    recharge = 2
    cap = 5

    await aioredis.delete(key)
    for i in range(cap):
        peek = await sut.peek(key, cap, recharge)
        assert peek.success
        assert peek.level == i
        res = await sut.consume(key, cap, recharge, block_duration=block_duration)
        assert res.success
        assert res.level == i + 1
        assert (recharge - 1) < res.until_next_drop <= recharge
        assert res.blocked_for is None

    peek = await sut.peek(key, cap, recharge)
    assert not peek.success
    assert peek.level == cap

    # This will block us.
    res = await sut.consume(key, cap, recharge, block_duration=block_duration)
    assert not res.success
    assert res.blocked_for == 1

    peek = await sut.peek(key, cap, recharge)
    assert not peek.success
    assert peek.level == cap
    assert peek.blocked_for is not None and 0.8 <= peek.blocked_for < 1

    res = await sut.consume(key, cap, recharge, block_duration=block_duration)
    assert not res.success
    assert res.blocked_for is not None and 0.8 <= res.blocked_for < 1

    await sleep(block_duration)
    # The block should have expired.

    peek = await sut.peek(key, cap, recharge)
    assert not peek.success
    assert peek.level == cap
    assert peek.blocked_for is None

    # This will block again.
    res = await sut.consume(key, cap, recharge, block_duration=block_duration)
    assert not res.success
    assert res.blocked_for is not None and 0.8 <= res.blocked_for <= 1
    peek = await sut.peek(key, cap, recharge)
    assert not peek.success
    assert peek.level == cap
    assert peek.blocked_for is not None and 0.8 <= peek.blocked_for < 1

    # Wait out the block and recharge.
    await sleep(1.0)

    peek = await sut.peek(key, cap, recharge)
    assert peek.success
    assert peek.level == cap - 1


@pytest.mark.asyncio
async def test_no_block_expires(aioredis):
    sut = Throttler(aioredis)

    key = "test_key"
    await sut.redis.delete(key)
    recharge = 1

    for capacity in range(1, 4):
        for i in range(capacity):
            peek = await sut.peek(key, capacity, recharge)
            assert peek.success
            assert peek.level == i
            res = await sut.consume(key, capacity, recharge)
            assert res.success
            assert res.level == i + 1
            assert (recharge - 1) < res.until_next_drop <= recharge
            assert res.blocked_for is None

        peek = await sut.peek(key, capacity, recharge)
        assert not peek.success
        assert peek.level == capacity
        res = await sut.consume(key, capacity, recharge)
        assert not res.success

        await sleep(capacity * recharge)
        assert not (await sut.redis.exists(key)), "Key not expired"


@pytest.mark.asyncio
async def test_optimized_key_expire(aioredis):
    sut = Throttler(aioredis)

    key = "test_key"
    await sut.redis.delete(key)

    await sut.consume(key, 100, 1.0, amount=2)
    assert (await sut.peek(key, 100, 1.0)).level == 2
    await sleep(1.0)
    assert await sut.redis.exists(key), "Key expired prematurely"
    await sleep(1.0)
    assert not (await sut.redis.exists(key)), "Key not expired"
