from typing import Any, Union

LuaArg = Union[str, int, float]

class ScriptingCommandsMixin:
    async def eval(
        self, script: str, keys: list[LuaArg] = [], args: list[LuaArg] = []
    ) -> Any: ...
