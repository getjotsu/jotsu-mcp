class CredentialsManager:
    async def load(self, server_id: str) -> dict | None:
        ...

    async def store(self, server_id: str, credentials: dict) -> None:
        ...

    async def get_access_token(self, server_id: str) -> str | None:
        credentials = await self.load(server_id)
        if credentials:
            return credentials.get('access_token')
        return None
