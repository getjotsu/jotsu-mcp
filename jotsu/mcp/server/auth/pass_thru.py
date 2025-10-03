import logging

from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.server.auth.provider import (
    AuthorizationParams, AuthorizationCode,
    RefreshToken, AccessToken
)

from jotsu.mcp.client import OAuth2AuthorizationCodeClient
from jotsu.mcp.server.cache import AsyncCache
from jotsu.mcp.server.client_manager import AsyncClientManager

from .base import BaseAuthServerProvider

logger = logging.getLogger(__name__)


class PassThruAuthServerProvider(BaseAuthServerProvider):
    # NOTE: these methods are declared in the order they are called.  See comments in parent class.
    def __init__(
            self, *,
            issuer_url: str,
            cache: AsyncCache,
            client_manager: AsyncClientManager,
            secret_key: str,
            authorization_endpoint: str, token_endpoint: str,
            scope: str | None = None
    ):
        self.authorization_endpoint = authorization_endpoint
        self.token_endpoint = token_endpoint
        self.scope = scope
        super().__init__(issuer_url=issuer_url, cache=cache, secret_key=secret_key, client_manager=client_manager)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        raise NotImplementedError()

    async def authorize(
            self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        oauth = self._oauth(client)
        return await self._authorize(oauth, params)

    # flow:
    #  - the third-party server redirects back to our custom redirect.
    #  - load_authorization_code

    async def exchange_authorization_code(
            self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        oauth = self._oauth(client)
        return await self._exchange_authorization_code(oauth, client, authorization_code)

    # load_refresh_token

    async def exchange_refresh_token(
            self,
            client: OAuthClientInformationFull,
            refresh_token: RefreshToken,
            scopes: list[str],
    ) -> OAuthToken | None:
        oauth = self._oauth(client)
        return await self._exchange_refresh_token(oauth, client, refresh_token, scopes)

    # load_access_token

    async def revoke_token(
            self,
            token: AccessToken | RefreshToken,
    ) -> None:
        raise NotImplementedError()

    def _oauth(self, client: OAuthClientInformationFull):
        return OAuth2AuthorizationCodeClient(
            authorization_endpoint=self.authorization_endpoint,
            token_endpoint=self.token_endpoint,
            scope=client.scope,
            client_id=client.client_id,
            client_secret=client.client_secret
        )
