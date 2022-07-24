from asyncio import sleep

from aioredis import Redis
from aiosteady.leakybucket import Throttler, ThrottleResult
from pytest import approx


async def test_no_block_quick(aioredis: Redis) -> None:
    cap = 10
    recharge = 5
    sut = Throttler(aioredis, cap, recharge)

    key = "test_key"

    await aioredis.delete(key)
    for i in range(10):
        peek = await sut.peek(key)
        assert peek.success
        assert peek.level == i
        res = await sut.consume(key)
        assert res.success
        assert res.level == i + 1
        assert (recharge - 1) < res.until_next_drop <= recharge
        assert res.blocked_for is None

    peek = await sut.peek(key)
    assert not peek.success
    assert peek.level == cap
    res = await sut.consume(key)
    assert not res.success


async def test_block(aioredis: Redis) -> None:
    recharge = 2
    cap = 5
    block_duration = 1
    sut = Throttler(aioredis, cap, recharge, block_duration=block_duration)

    key = "test_key"

    await aioredis.delete(key)
    for i in range(cap):
        peek = await sut.peek(key)
        assert peek.success
        assert peek.level == i
        res = await sut.consume(key)
        assert res.success
        assert res.level == i + 1
        assert (recharge - 1) < res.until_next_drop <= recharge
        assert res.blocked_for is None

    peek = await sut.peek(key)
    assert not peek.success
    assert peek.level == cap

    # This will block us.
    res = await sut.consume(key)
    assert not res.success
    assert res.blocked_for == 1

    peek = await sut.peek(key)
    assert not peek.success
    assert peek.level == cap
    assert peek.blocked_for is not None and 0.8 <= peek.blocked_for < 1

    res = await sut.consume(key)
    assert not res.success
    assert res.blocked_for is not None and 0.8 <= res.blocked_for < 1

    await sleep(block_duration)
    # The block should have expired.

    peek = await sut.peek(key)
    assert not peek.success
    assert peek.level == cap
    assert peek.blocked_for is None

    # This will block again.
    res = await sut.consume(key)
    assert not res.success
    assert res.blocked_for is not None and 0.8 <= res.blocked_for <= 1
    peek = await sut.peek(key)
    assert not peek.success
    assert peek.level == cap
    assert peek.blocked_for is not None and 0.8 <= peek.blocked_for < 1

    # Wait out the block and recharge.
    await sleep(1.0)

    peek = await sut.peek(key)
    assert peek.success
    assert peek.level == cap - 1


async def test_expire_no_block(aioredis: Redis) -> None:
    """The key expires properly, no blocking."""
    recharge = 1

    key = "test_key"
    await aioredis.delete(key)

    for capacity in range(1, 4):
        sut = Throttler(aioredis, capacity, recharge)

        for i in range(capacity):
            peek = await sut.peek(key)
            assert peek.success
            assert peek.level == i
            res = await sut.consume(key)
            assert res.success
            assert res.level == i + 1
            assert (recharge - 1) < res.until_next_drop <= recharge
            assert res.blocked_for is None

        peek = await sut.peek(key)
        assert not peek.success
        assert peek.level == capacity
        res = await sut.consume(key)
        assert not res.success
        assert res.level == capacity

        await sleep(capacity * recharge)
        assert await sut.peek(key) == ThrottleResult(True, 0, recharge, None)

        # Due to optimizations in the lua script, the key may actually live up to 1
        # recharge period longer.
        await sleep(recharge)
        ttl = await aioredis.pttl(key)
        assert ttl == -2, "Key not expired"


async def test_optimized_key_expire(aioredis: Redis) -> None:
    cap = 100
    recharge = 1.0
    sut = Throttler(aioredis, cap, recharge)

    key = "test_key"
    await aioredis.delete(key)

    await sut.consume(key, amount=2)
    assert (await sut.peek(key)).level == 2
    await sleep(1.0)
    assert await aioredis.exists(key), "Key expired prematurely"

    # Due to optimizations in the lua script, the key may actually live up to 1
    # recharge period longer.
    await sleep(recharge + 1)
    ttl = await aioredis.pttl(key)
    assert ttl == -2, "Key not expired"


async def test_recharge(aioredis: Redis) -> None:
    """Drops can be drained/the throttler recharged."""
    cap = 3
    recharge = 5
    sut = Throttler(aioredis, cap, recharge)

    key = "recharge_test"
    await aioredis.delete(key)

    r = await sut.consume(key, 3)
    assert r.level == 3
    assert approx(r.until_next_drop, recharge)

    r2 = await sut.consume(key, -1)
    assert r2.level == 2
    assert approx(r2.until_next_drop, recharge - 0.05)

    r3 = await sut.consume(key, -5)
    assert r3.level == 0
    assert not await aioredis.exists(key)
    assert approx(r3.until_next_drop, recharge)
