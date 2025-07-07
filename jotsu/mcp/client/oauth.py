import logging
import secrets
import typing
from urllib.parse import urlencode

import httpx
import pydantic

from mcp.server.auth.handlers.token import (
    AuthorizationCodeRequest as BaseAuthorizationCodeRequest,
    RefreshTokenRequest
)
from mcp.server.auth.provider import RefreshToken
from mcp.shared.auth import OAuthToken, OAuthClientInformationFull

from . import utils

logger = logging.getLogger(__name__)


class AuthorizeInfo(pydantic.BaseModel):
    url: str
    response_type: typing.Literal['code'] = 'code'
    client_id: str
    redirect_uri: str
    scope: str
    state: str


# Same as MCP, but make code_verifier optional.
class AuthorizationCodeRequest(BaseAuthorizationCodeRequest):
    code_verifier: str | None = pydantic.Field(default=None, description='PKCE code verifier')


class ServerMeta(pydantic.BaseModel):
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str | None


async def log_request(request: httpx.Request):
    logging.info(f'Request: {request.method} {request.url}')
    logging.info(f'Headers: {request.headers}')
    if request.content:
        logging.info(f'Body: {request.content.decode()}')


class OAuth2AuthorizationCodeClient:
    """Client for the OAuth2.1 flow required by MCP."""

    def __init__(
            self, *,
            authorization_endpoint: str, token_endpoint: str,
            scope: str,
            client_id: str, client_secret: str | None = None,
            **_kwargs  # ignored
    ):
        self.authorization_endpoint = authorization_endpoint
        self.token_endpoint = token_endpoint
        self.scope = scope
        self.client_id = client_id
        self.client_secret = client_secret

    @classmethod
    def generate_state(cls):
        return secrets.token_hex(16)

    async def authorize_info(self, *, redirect_uri: str, state: str = None) -> AuthorizeInfo:
        """Generate an authorization URL"""
        state = state if state else self.generate_state()
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'scope': self.scope,
            'state': state
        }
        url = f'{self.authorization_endpoint}?{urlencode(params)}'
        params['url'] = url
        return AuthorizeInfo(**params)

    async def exchange_authorization_code(
            self, *, code: str, redirect_uri: str, code_verifier: str | None = None
    ) -> OAuthToken:
        """Call the authorization endpoint to obtain an access token."""

        async with httpx.AsyncClient(event_hooks={'request': [log_request]}) as httpx_client:
            req = AuthorizationCodeRequest(
                grant_type='authorization_code',
                code=code,
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=pydantic.AnyHttpUrl(redirect_uri)
            )
            if code_verifier:
                req.code_verifier = code_verifier
            res = await httpx_client.post(
                self.token_endpoint,
                data=req.model_dump(mode='json', exclude_unset=True),
                auth=(self.client_id, self.client_secret)
            )
            if res.status_code != 200:
                logger.warning('%d %s: %s', res.status_code, res.reason_phrase, res.text)
            res.raise_for_status()

            logger.debug('exchange_authorization_code: %s', res.text)
            token = res.json()
            token['token_type'] = 'bearer'  # sometimes the response is 'Bearer' with a capital 'B'.

            return OAuthToken(**token)

    async def exchange_refresh_token(
            self,
            refresh_token: RefreshToken,
            scopes: list[str],
    ) -> OAuthToken | None:
        async with httpx.AsyncClient(event_hooks={'request': [log_request]}) as httpx_client:
            req = RefreshTokenRequest(
                grant_type='refresh_token',
                refresh_token=refresh_token.token,
                scope=' '.join(scopes) if scopes else self.scope,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            res = await httpx_client.post(self.token_endpoint, data=req.model_dump())
            if res.status_code != 200:
                logger.warning('Could not refresh access token: [%d] %s', res.status_code, res.text)
                return None

            return OAuthToken(**res.json())

    @classmethod
    async def server_metadata_discovery(cls, base_url: str) -> ServerMeta:
        """
        Server Metadata Discovery
        https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization#2-3-server-metadata-discovery
        Try to get server endpoints automatically or fallback to defaults.
        :param base_url:
        :return:
        """
        # Server Metadata Discovery (SHOULD)
        url = utils.server_url('/.well-known/oauth-authorization-server', url=base_url)
        logger.debug('Trying server metadata discovery at %s', url)
        try:
            async with httpx.AsyncClient(event_hooks={'request': [log_request]}) as httpx_client:
                res = await httpx_client.get(url)
                res.raise_for_status()
                logger.info('Server metadata found: %s', res.text)
                return ServerMeta(**res.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info('Server metadata discovery not found, using default endpoints')
                return ServerMeta(
                    authorization_endpoint=utils.server_url('/authorize', url=base_url),
                    token_endpoint=utils.server_url('/token', url=base_url),
                    registration_endpoint=utils.server_url('/register', url=base_url)
                )
            else:
                raise e

    @classmethod
    async def dynamic_client_registration(
            cls, registration_endpoint: str, redirect_uris: typing.List[str]
    ) -> OAuthClientInformationFull:
        """
        Dynamic Client Registration
        :param registration_endpoint:
        :param redirect_uris:
        :return:
        """
        logger.debug('Trying dynamic client registration at %s', registration_endpoint)

        async with httpx.AsyncClient() as httpx_client:
            res = await httpx_client.post(registration_endpoint, json={'redirect_uris': redirect_uris})
            res.raise_for_status()

            client = res.json()
            assert 'code' in client['response_types']
            logger.debug('Client registration successful: %s', res.text)
            return OAuthClientInformationFull(**client)
