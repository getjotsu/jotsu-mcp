from jotsu.mcp.server import AsyncCache


class AsyncMemoryCache(AsyncCache):
    def __init__(self):
        self.cache = {}

    async def get(self, key: str):
        return self.cache.get(key)

    async def set(self, key: str, value, expires_in: int | None = None):
        # Ignore expiration in local mode.
        if value is not None:
            self.cache[key] = value
        else:
            self.cache.pop(key, None)

    async def delete(self, key: str):
        self.cache.pop(key, None)
