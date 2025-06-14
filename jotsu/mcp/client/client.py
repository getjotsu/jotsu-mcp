import json
import logging
import typing
import urllib.parse
from queue import Queue
from contextlib import asynccontextmanager

import httpx

if typing.TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.auth.provider import RefreshToken

from jotsu.mcp.common import WorkflowServer, WorkflowServerFull
from . import utils
from .credentials import CredentialsManager, LocalCredentialsManager
from .oauth import OAuth2AuthorizationCodeClient

logger = logging.getLogger(__name__)


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
    def __init__(self, *, credentials_manager: CredentialsManager = None):
        self._credentials: CredentialsManager = \
            credentials_manager if credentials_manager else LocalCredentialsManager()

    @property
    def credentials(self):
        return self._credentials

    @asynccontextmanager
    async def _connect(self, server: WorkflowServer, headers: httpx.Headers):
        async with streamablehttp_client(
                url=str(server.url),
                headers=headers,
        ) as (read_stream, write_stream, _):
            async with MCPClientSession(read_stream, write_stream, server=server, client=self) as session:
                await session.initialize()
                yield session

    @asynccontextmanager
    async def session(self, server: WorkflowServer, headers: httpx.Headers | None = None):
        headers = headers if headers else httpx.Headers()
        access_token = await self.credentials.get_access_token(server.id)
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'

        try:
            async with self._connect(server, headers) as session:
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

        refresh_token = RefreshToken(**credentials)
        token = await oauth.exchange_refresh_token(refresh_token=refresh_token, scopes=[])
        if token:
            # Keep values not included in the token response, like the endpoints.
            credentials = {**credentials, **token.model_dump(mode='json')}
            await self.credentials.store(server.id, credentials)
            return token.access_token
        return None

    async def authenticate(self, server: WorkflowServer) -> str | None:
        """Do the OAuth2 authorization code flow.  Returns an access token if successful."""
        return None


class LocalMCPClient(MCPClient):

    def __init__(self, *, request_handler: 'BaseHTTPRequestHandler' = None, **kwargs):
        super().__init__(**kwargs)
        self._request_handler = request_handler

    async def authenticate(self, server: WorkflowServer) -> str | None:
        import threading
        import webbrowser

        import pkce
        from . import localserver

        # Try refresh first instead of forcing the user to re-authenticate.
        credentials = await self.credentials.load(server.id)
        if credentials:
            access_token = await self.token_refresh(server, credentials)
            if access_token:
                return access_token

        base_url = utils.server_url('', url=str(server.url))

        # Server Metadata Discovery (SHOULD)
        server_metadata = await OAuth2AuthorizationCodeClient.server_metadata_discovery(base_url=base_url)

        # Dynamic Client Registration (SHOULD)
        # NOTE: fail if the server doesn't support DCR.
        client_info = await OAuth2AuthorizationCodeClient.dynamic_client_registration(
            registration_endpoint=server_metadata.registration_endpoint, redirect_uris=['http://localhost:8001/']
        )

        queue = Queue()
        httpd = localserver.LocalHTTPServer(queue, request_handler=self._request_handler)
        t = threading.Thread(target=httpd.serve_forever)
        t.daemon = True
        t.start()

        code_verifier, code_challenge = pkce.generate_pkce_pair()

        redirect_uri = urllib.parse.quote('http://localhost:8001/')
        url = f'{server_metadata.authorization_endpoint}?client_id={client_info.client_id}' + \
              f'&response_type=code&code_challenge={code_challenge}&redirect_uri={redirect_uri}'
        print(f'Opening a link in your default browser: {url}')
        webbrowser.open(url)

        # The local webserver writes an event to the queue on success.
        params = queue.get(timeout=120)
        logger.debug('Browser authentication complete: %s', json.dumps(params))
        code = params.get('code')   # this is a list
        if not code:
            logger.error('Authorization failed, likely due to being canceled.')
            return None

        logger.debug('Exchanging authorization code for token at %s', server_metadata.token_endpoint)

        client = OAuth2AuthorizationCodeClient(
            **client_info.model_dump(mode='json'),
            authorize_endpoint=server_metadata.authorization_endpoint,
            token_endpoint=server_metadata.token_endpoint
        )
        token = await client.exchange_authorization_code(
            code=code[0],
            code_verifier=code_verifier,
            redirect_uri='http://localhost:8001/'
        )

        credentials = {
            **token.model_dump(mode='json'),
            'client_id': client_info.client_id,
            'client_secret': client_info.client_secret,
            'authorization_endpoint': server_metadata.authorization_endpoint,
            'token_endpoint': server_metadata.token_endpoint,
            'registration_endpoint': server_metadata.registration_endpoint
        }

        await self.credentials.store(server.id, credentials)
        return token.access_token
