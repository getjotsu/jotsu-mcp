import logging
import time

import httpx
import jwt
from mcp.server.auth.provider import OAuthAuthorizationServerProvider, RefreshToken, AccessToken, AuthorizationCode, \
    AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.exceptions import HTTPException

from jotsu.mcp.client import OAuth2AuthorizationCodeClient
from jotsu.mcp.client.utils import server_url
from jotsu.mcp.server.cache import AsyncCache
from jotsu.mcp.server.client_manager import AsyncClientManager
from jotsu.mcp.server import utils

logger = logging.getLogger(__name__)


class BaseAuthServerProvider(OAuthAuthorizationServerProvider):
    # NOTE: these methods are declared in the order they are called.  See comments in parent class.
    def __init__(
            self, *,
            issuer_url: str,
            cache: AsyncCache,
            client_manager: AsyncClientManager,
            secret_key: str,
    ):
        self.issuer_url = issuer_url  # only needed for the intermediate redirect.
        self.cache = cache
        self.client_manager = client_manager
        self.secret_key = secret_key
        super().__init__()

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return await self.client_manager.get_client(client_id)

    async def _authorize(
            self, oauth: OAuth2AuthorizationCodeClient, params: AuthorizationParams
    ) -> str:
        redirect_uri = self._redirect_uri()

        # If the client passed us a state value, use it, otherwise use authlib to generate one.
        params.state = params.state if params.state else oauth.generate_state()
        await utils.cache_set(self.cache, params.state, params)

        logger.info(
            'authorize: %s, redirect_uri=%s, state=%s', params.model_dump_json(), redirect_uri, params.state
        )

        auth_info = await oauth.authorize_info(redirect_uri=redirect_uri, state=params.state)
        logger.info('authorize -> %s', auth_info.url)
        return auth_info.url

    async def _exchange_authorization_code(
            self,
            oauth: OAuth2AuthorizationCodeClient,
            client: OAuthClientInformationFull,
            authorization_code: AuthorizationCode
    ) -> OAuthToken:
        # This server redirect which was registered with the downstream provider.
        redirect_uri = server_url('/redirect', url=self.issuer_url)

        logger.info(
            'exchange_authorization_code: %s, redirect_uri=%s',
            authorization_code.model_dump_json(), redirect_uri
        )

        try:
            third_party_token = await oauth.exchange_authorization_code(
                code=authorization_code.code, redirect_uri=redirect_uri
            )
            return self._third_party_token_to_oauth_token(client, third_party_token)
        except httpx.HTTPStatusError as e:
            logger.error('oauth error [%d]: %s', e.response.status_code, e.response.text)
            raise HTTPException(status_code=500, detail=e.response.text)
        except Exception as e:  # noqa
            logger.exception('oauth error')
            raise HTTPException(status_code=500, detail=str(e))

    async def load_authorization_code(
            self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode:
        """OAuth2 flow, step 2: exchange the authorization code for access token
        """
        logger.info('load_authorization_code: %s %s', authorization_code, client.model_dump_json())
        params = await utils.cache_get(self.cache, authorization_code, AuthorizationParams)

        # This is the last use of the cached code.
        await self.cache.delete(authorization_code)

        return AuthorizationCode(
            code=authorization_code,
            scopes=client.scope.split(' ') if client.scope else [],
            expires_at=time.time() + 10 * 60,  # Default, let the third-party server catch this value.
            client_id=client.client_id,
            redirect_uri=params.redirect_uri,  # base value, without params
            redirect_uri_provided_explicitly=True,
            code_challenge=params.code_challenge
        )

    async def load_refresh_token(
            self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        logger.debug('load_refresh_token: %s', refresh_token)

        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=['HS256'])
        except jwt.exceptions.InvalidTokenError as e:
            # InvalidTokenError includes DecodeError and ExpiredSignatureError
            logger.info('Invalid refresh JWT: %s', str(e))
            return None

        return RefreshToken(
            token=payload['token'],
            client_id=payload['client_id'],
            scopes=payload['scopes'],
            expires_at=payload['expires_at']
        )

    async def _exchange_refresh_token(
            self,
            oauth: OAuth2AuthorizationCodeClient,
            client: OAuthClientInformationFull,
            refresh_token: RefreshToken,
            scopes: list[str],
    ) -> OAuthToken | None:
        logger.debug('exchange_refresh_token: %s', refresh_token.model_dump_json())
        third_party_token = await oauth.exchange_refresh_token(refresh_token=refresh_token, scopes=scopes)
        return self._third_party_token_to_oauth_token(client, third_party_token) if third_party_token else None

    async def load_access_token(self, token: str) -> AccessToken | None:
        logger.debug('load_access_token: %s', token)

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
        except jwt.exceptions.InvalidTokenError as e:
            # InvalidTokenError includes DecodeError and ExpiredSignatureError
            logger.info('Invalid access JWT: %s', str(e))
            return None

        return AccessToken(
            token=payload['token'],
            client_id=payload['client_id'],
            scopes=payload['scopes'],
            expires_at=payload['expires_at']
        )

    def _redirect_uri(self):
        return server_url('/redirect', url=self.issuer_url)

    def _generate_jwt(self, token: AccessToken | RefreshToken) -> str:
        payload = {
            **token.model_dump(),
            'exp': token.expires_at,
            'iat': time.time(),
            'sub': token.client_id
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def _third_party_token_to_oauth_token(
            self, client: OAuthClientInformationFull, third_party_token: OAuthToken
    ) -> OAuthToken:
        logger.debug('third-party token: %s', third_party_token.model_dump_json())

        # Convert the simple string tokens returned by the third-party app to JWTs.
        # This gives us the information we need later in load_access_token()/load_refresh_token()
        access_token = self._generate_jwt(
            AccessToken(
                token=third_party_token.access_token,
                expires_at=int(time.time() + third_party_token.expires_in) if third_party_token.expires_in else None,
                client_id=client.client_id,
                scopes=[client.scope] if client.scope else []
            )
        )
        refresh_token = self._generate_jwt(
            RefreshToken(
                token=third_party_token.refresh_token,
                expires_at=None,  # no expires_at, just have the client try it.
                client_id=client.client_id,
                scopes=[client.scope] if client.scope else []
            )
        ) if third_party_token.refresh_token else None

        logger.debug('access_token: %s, expires_in=%s', access_token, third_party_token.expires_in)

        return OAuthToken(
            access_token=access_token,
            expires_in=third_party_token.expires_in,
            scope=client.scope,
            refresh_token=refresh_token
        )
