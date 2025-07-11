import logging
import re
import typing
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.auth.provider import RefreshToken

from jotsu.mcp.types import WorkflowServer
from jotsu.mcp.types.models import WorkflowServerFull

from . import utils
from .credentials import CredentialsManager, MemoryCredentialsManager
from .oauth import OAuth2AuthorizationCodeClient

logger = logging.getLogger(__name__)


def split_scopes(scope: str) -> typing.List[str]:
    return [s.strip() for s in re.split(r'\s+', scope) if s]


class MCPClientSession(ClientSession):
    def __init__(self, *args, client: 'MCPClient', server: WorkflowServer, **kwargs):
        self._client = client
        self._server = WorkflowServerFull(**server.model_dump(), tools=[], resources=[], prompts=[])
        super().__init__(*args, **kwargs)

    @property
    def server(self):
        return self._server

    async def load(self) -> WorkflowServerFull:
        result = await self.list_tools()
        self._server.tools.extend(result.tools)
        result = await self.list_resources()
        self._server.resources.extend(result.resources)
        result = await self.list_prompts()
        self._server.prompts.extend(result.prompts)
        return self._server


class MCPClient:
    def __init__(self, *, credentials_manager: CredentialsManager | None = None):
        self._credentials = credentials_manager if credentials_manager else MemoryCredentialsManager()

    @property
    def credentials(self):
        return self._credentials

    @asynccontextmanager
    async def _connect(
            self, server: WorkflowServer, headers: httpx.Headers, timeout: timedelta = timedelta(seconds=30)
    ):
        async with streamablehttp_client(
                url=str(server.url),
                timeout=timeout,
                headers=headers,
        ) as (read_stream, write_stream, _):
            async with MCPClientSession(read_stream, write_stream, server=server, client=self) as session:
                await session.initialize()
                yield session

    @asynccontextmanager
    async def session(
            self, server: WorkflowServer, headers: httpx.Headers | None = None,
            *, timeout: timedelta = timedelta(seconds=30)
    ):
        headers = headers if headers else httpx.Headers()
        if 'Authorization' not in headers:
            access_token = await self.credentials.get_access_token(server.id)
            if access_token:
                headers['Authorization'] = f'Bearer {access_token}'

        try:
            async with self._connect(server, headers, timeout=timeout) as session:
                yield session
        except BaseExceptionGroup as e:
            if not utils.is_httpx_401_exception(e):
                raise e

            access_token = await self.authenticate(server)
            if access_token:
                headers['Authorization'] = f'Bearer {access_token}'

            async with self._connect(server, headers) as session:
                yield session

    async def token_refresh(self, server: WorkflowServer, credentials: dict) -> str | None:
        """ Try to use our refresh token to get a new access token. """
        oauth = OAuth2AuthorizationCodeClient(**credentials)
        token = credentials.get('refresh_token')
        if token:
            scopes = []
            scope = credentials.get('scope')
            if scope:
                scopes = split_scopes(scope)  # multiple scopes are delimited by spaces.

            refresh_token = RefreshToken(**credentials, token=token, scopes=scopes)
            oauth_token = await oauth.exchange_refresh_token(refresh_token=refresh_token, scopes=[])
            if oauth_token:
                # Keep values not included in the token response, like the endpoints.
                credentials = {**credentials, **oauth_token.model_dump(mode='json')}
                await self.credentials.store(server.id, credentials)
                return oauth_token.access_token
        return None

    async def authenticate(self, server: WorkflowServer) -> str | None:
        """Do the OAuth2 authorization code flow.  Returns an access token if successful."""
        return None
