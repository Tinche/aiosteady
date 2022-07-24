from hashlib import sha1
from importlib.resources import read_text
from typing import Final, Optional

from aioredis.commands.scripting import ScriptingCommandsMixin
from aioredis.errors import ReplyError
from attr import frozen

SCRIPT_CONSUME: Final = read_text(__package__, "leakybucket_consume.lua")
_SCRIPT_CONSUME_SHA1: Final = sha1(SCRIPT_CONSUME.encode("utf8")).hexdigest()
SCRIPT_PEEK: Final = read_text(__package__, "leakybucket_peek.lua")
_SCRIPT_PEEK_SHA1: Final = sha1(SCRIPT_PEEK.encode("utf8")).hexdigest()


@frozen
class ThrottleResult:
    success: bool  # Whether the bucket had sufficient capacity.
    level: int  # The level of the bucket.
    until_next_drop: float  # In seconds.
    blocked_for: Optional[float]  # In seconds.


@frozen
class Throttler:
    redis: ScriptingCommandsMixin
    max_capacity: int
    drop_recharge: float
    block_duration: Optional[float] = None

    async def consume(
        self,
        key: str,
        amount: int = 1,
    ) -> ThrottleResult:
        """Attempt adding a number of drops from the bucket.

        If the amount is negative, drops are removed from the bucket up to 0.
        """
        try:
            success, block_remaining, level, to_next = await self.redis.evalsha(
                _SCRIPT_CONSUME_SHA1,
                [key],
                [
                    self.max_capacity,
                    str(self.drop_recharge),
                    self.block_duration or 0,
                    amount,
                ],
            )
        except ReplyError:
            success, block_remaining, level, to_next = await self.redis.eval(
                SCRIPT_CONSUME,
                [key],
                [
                    self.max_capacity,
                    str(self.drop_recharge),
                    self.block_duration or 0,
                    amount,
                ],
            )

        return ThrottleResult(
            bool(success),
            level,
            float(to_next),
            br if (br := float(block_remaining)) != 0.0 else None,
        )

    async def peek(
        self,
        key: str,
    ) -> ThrottleResult:
        """Only peek at the bucket, without changing it."""
        try:
            block_remaining, level, to_next = await self.redis.evalsha(
                _SCRIPT_PEEK_SHA1,
                [key],
                [self.max_capacity, str(self.drop_recharge)],
            )
        except ReplyError:
            block_remaining, level, to_next = await self.redis.eval(
                SCRIPT_PEEK,
                [key],
                [self.max_capacity, str(self.drop_recharge)],
            )

        br = br if (br := float(block_remaining)) != 0.0 else None

        return ThrottleResult(
            br is None and (level < self.max_capacity),
            level,
            float(to_next),
            br,
        )
