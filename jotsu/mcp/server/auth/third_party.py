import logging

from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.server.auth.provider import (
    AuthorizationParams, AuthorizationCode,
    RefreshToken, AccessToken
)

from jotsu.mcp.client import OAuth2AuthorizationCodeClient

from jotsu.mcp.server.client_manager import AsyncClientManager
from jotsu.mcp.server.cache import AsyncCache
from .base import BaseAuthServerProvider

logger = logging.getLogger(__name__)


class ThirdPartyAuthServerProvider(BaseAuthServerProvider):
    # NOTE: these methods are declared in the order they are called.  See comments in parent class.
    def __init__(
            self, *,
            issuer_url: str,
            cache: AsyncCache,
            oauth: OAuth2AuthorizationCodeClient,
            secret_key: str,
            client_manager: AsyncClientManager,
    ):
        self.client_manager = client_manager
        self.oauth = oauth
        super().__init__(issuer_url=issuer_url, cache=cache, secret_key=secret_key, client_manager=client_manager)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        logger.info('Registering client ... %s', client_info.model_dump_json())
        try:
            await self.client_manager.save_client(client_info)
            logger.debug('Registered client: %s', client_info.client_id)
        except Exception as e:  # noqa
            logger.exception('Client registration failed.')
            raise e

    async def authorize(
            self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        assert params.redirect_uri in client.redirect_uris  # do better
        return await self._authorize(self.oauth, params)

    # flow:
    #  - the third-party server redirects back to our custom redirect.
    #  - load_authorization_code

    async def exchange_authorization_code(
            self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        return await self._exchange_authorization_code(self.oauth, client, authorization_code)

    # load_refresh_token

    async def exchange_refresh_token(
            self,
            client: OAuthClientInformationFull,
            refresh_token: RefreshToken,
            scopes: list[str],
    ) -> OAuthToken | None:
        return await self._exchange_refresh_token(self.oauth, client, refresh_token, scopes)

    # load_access_token

    async def revoke_token(
            self,
            token: AccessToken | RefreshToken,
    ) -> None:
        logger.info('revoke_token: %s', token)
        ...
