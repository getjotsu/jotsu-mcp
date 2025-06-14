from mcp.shared.auth import OAuthClientInformationFull


class AsyncClientManager:
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        ...

    async def save_client(self, client: OAuthClientInformationFull | None) -> None:
        ...
