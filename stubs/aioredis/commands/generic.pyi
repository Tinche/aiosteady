class GenericCommandsMixin:
    async def delete(self, key: str, *keys: str): ...