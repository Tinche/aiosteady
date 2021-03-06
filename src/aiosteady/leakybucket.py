from typing import Optional
from attr import frozen
from aioredis.commands.scripting import ScriptingCommandsMixin
from importlib.resources import read_text

SCRIPT_CONSUME = read_text(__package__, "leakybucket_consume.lua")
SCRIPT_PEEK = read_text(__package__, "leakybucket_peek.lua")


@frozen
class ThrottleResult:
    success: bool  # Whether the bucket had sufficient capacity.
    level: int  # The level of the bucket.
    until_next_drop: float  # In seconds.
    blocked_for: Optional[float]  # In seconds.


@frozen
class Throttler:
    redis: ScriptingCommandsMixin

    async def consume(
        self,
        key,
        max_capacity: int,
        drop_recharge: float,
        amount=1,
        block_duration: Optional[float] = None,
    ) -> ThrottleResult:
        """Attempt consuming a number of drops from the bucket."""
        success, block_remaining, level, to_next = await self.redis.eval(
            SCRIPT_CONSUME,
            [key],
            [max_capacity, str(drop_recharge), block_duration or 0, amount],
        )

        return ThrottleResult(
            bool(success),
            level,
            float(to_next),
            br if (br := float(block_remaining)) != 0.0 else None,
        )

    async def peek(
        self,
        key,
        max_capacity: int,
        drop_recharge: float,
    ) -> ThrottleResult:
        """"""
        block_remaining, level, to_next = await self.redis.eval(
            SCRIPT_PEEK,
            [key],
            [max_capacity, str(drop_recharge)],
        )

        br = br if (br := float(block_remaining)) != 0.0 else None

        return ThrottleResult(
            br is None and (level < max_capacity),
            level,
            float(to_next),
            br,
        )