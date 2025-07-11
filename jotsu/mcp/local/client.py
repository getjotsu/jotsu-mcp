import json
import logging
import typing
import urllib.parse
import threading
import webbrowser

from queue import Queue

from .credentials import LocalCredentialsManager

if typing.TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler

import pkce
from jotsu.mcp.types import WorkflowServer
from jotsu.mcp.client import MCPClient, OAuth2AuthorizationCodeClient, utils

from . import localserver


logger = logging.getLogger(__name__)


class LocalMCPClient(MCPClient):

    def __init__(self, *, request_handler: 'BaseHTTPRequestHandler' = None, **kwargs):
        if 'credentials_manager' not in kwargs:
            kwargs['credentials_manager'] = LocalCredentialsManager()

        super().__init__(**kwargs)
        self._request_handler = request_handler

    async def authenticate(self, server: WorkflowServer) -> str | None:
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
            authorization_endpoint=server_metadata.authorization_endpoint,
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
