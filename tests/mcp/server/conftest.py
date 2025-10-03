import pydantic
import pytest
from mcp.server.auth.provider import AuthorizationCode
from mcp.shared.auth import OAuthClientInformationFull

from jotsu.mcp.client import OAuth2AuthorizationCodeClient
from jotsu.mcp.local.cache import AsyncMemoryCache
from jotsu.mcp.server import ThirdPartyAuthServerProvider, AsyncClientManager
from jotsu.mcp.server.auth import PassThruAuthServerProvider


class MockAsyncClientManager(AsyncClientManager):
    def __init__(self):
        self._client = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._client.get(client_id)

    async def save_client(self, client: OAuthClientInformationFull | None) -> None:
        self._client[client.client_id] = client


@pytest.fixture(name='third_party_provider', scope='function')
def third_party_provider_fixture():
    oauth = OAuth2AuthorizationCodeClient(
        authorization_endpoint='https://example.com/authorize',
        token_endpoint='https://example.com/token',
        scope='identify',
        client_id='abc',
        client_secret='123'
    )

    return ThirdPartyAuthServerProvider(
        issuer_url='https://example.com',
        cache=AsyncMemoryCache(),
        oauth=oauth,
        client_manager=MockAsyncClientManager(),
        secret_key='s0secret'
    )


@pytest.fixture(name='pass_thru_provider', scope='function')
def pass_thru_provider_fixture():
    return PassThruAuthServerProvider(
        issuer_url='https://example.com',
        cache=AsyncMemoryCache(),
        secret_key='s0secret',
        authorization_endpoint='https://example.com/authorize',
        token_endpoint='https://example.com/token',
        client_manager=MockAsyncClientManager()
    )


@pytest.fixture(name='client_info', scope='function')
def client_info_fixture():
    return OAuthClientInformationFull(
        client_id='abc',
        redirect_uris=[pydantic.AnyHttpUrl('https://localhost/redirect')],
    )


@pytest.fixture(name='authorization_code', scope='function')
def authorization_code_fixture(client_info):
    return AuthorizationCode(
        code='123',
        scopes=[],
        expires_at=0,
        code_challenge='abc',
        client_id=client_info.client_id,
        redirect_uri=client_info.redirect_uris[0],
        redirect_uri_provided_explicitly=False
    )
