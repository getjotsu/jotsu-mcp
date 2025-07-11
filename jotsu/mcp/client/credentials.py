import typing


class CredentialsManager:
    async def load(self, server_id: str) -> dict | None:
        ...

    async def store(self, server_id: str, credentials: dict) -> None:
        ...

    async def get_access_token(self, server_id: str) -> str | None:
        credentials = await self.load(server_id)
        return credentials.get('access_token') if credentials else None


class MemoryCredentialsManager(CredentialsManager):

    def __init__(self, store: typing.Dict[str, dict] | None = None):
        self._store: typing.Dict[str, dict] = store if store else {}

    async def load(self, server_id: str) -> dict | None:
        return self._store.get(server_id)

    async def store(self, server_id: str, credentials: dict) -> None:
        self._store[server_id] = credentials
