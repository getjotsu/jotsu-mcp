from contextlib import asynccontextmanager

import pytest
import pydantic
import httpx

from mcp.shared.auth import OAuthToken

from jotsu.mcp.client import MCPClient
from jotsu.mcp.client.credentials import CredentialsManager
from jotsu.mcp.common import WorkflowServer


class MockCredentialsManager(CredentialsManager):
    async def load(self, server_id: str) -> dict | None:
        return {
            'access_token': 'xxx'
        }


@pytest.mark.asyncio
async def test_client():
    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))

    credentials_manager = MockCredentialsManager()

    client = MCPClient(credentials_manager=credentials_manager)
    async with client.session(server) as session:
        result = await session.call_tool('greet', {'name': 'World'})
        assert result.isError is False


@pytest.mark.asyncio
async def test_client_auth(mocker):

    req = httpx.Request('GET', 'https://example.com')
    res = httpx.Response(401)
    e = BaseExceptionGroup('error', [httpx.HTTPStatusError('xxx', request=req, response=res)])

    @asynccontextmanager
    async def mock_connect(*_args, **_kwargs):
        if not hasattr(mock_connect, 'called'):
            setattr(mock_connect, 'called', True)
            raise e
        obj = mocker.Mock()
        obj.call_tool = mocker.AsyncMock(return_value=True)
        yield obj

    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))

    credentials_manager = MockCredentialsManager()
    client = MCPClient(credentials_manager=credentials_manager)
    mocker.patch.object(client, '_connect', new=mock_connect)
    authenticate = mocker.patch.object(client, 'authenticate', return_value='xxx', new_callable=mocker.AsyncMock)

    async with client.session(server) as session:
        assert await session.call_tool('greet', {'name': 'World'})

    authenticate.assert_called_once()


async def test_client_error(mocker):
    req = httpx.Request('GET', 'https://example.com')
    res = httpx.Response(500)
    e = BaseExceptionGroup('error', [httpx.HTTPStatusError('xxx', request=req, response=res)])

    @asynccontextmanager
    async def mock_connect(*args, **_kwargs):
        raise e
        yield  # noqa

    credentials_manager = MockCredentialsManager()
    client = MCPClient(credentials_manager=credentials_manager)
    mocker.patch.object(client, '_connect', new=mock_connect)

    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    with pytest.raises(BaseExceptionGroup):
        async with client.session(server):
            ...


async def test_refresh_token(mocker):
    token = OAuthToken(access_token='xxx')

    credentials_manager = MockCredentialsManager()
    client = MCPClient(credentials_manager=credentials_manager)
    exchange_refresh_token = mocker.patch(
        'jotsu.mcp.client.OAuth2AuthorizationCodeClient.exchange_refresh_token',
        new_callable=mocker.AsyncMock, return_value=token
    )

    credentials = {
        'token': 'xxx', 'client_id': '123', 'scopes': [],
        'authorization_endpoint': 'https://example.com/authorize',
        'token_endpoint': 'https://example.com./tokens',
        'scope': '',
        'client_secret': 'xyz'
    }

    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    assert await client.token_refresh(server, credentials)

    exchange_refresh_token.assert_called_once()


async def test_refresh_failed(mocker):
    credentials_manager = MockCredentialsManager()
    client = MCPClient(credentials_manager=credentials_manager)
    exchange_refresh_token = mocker.patch(
        'jotsu.mcp.client.OAuth2AuthorizationCodeClient.exchange_refresh_token',
        new_callable=mocker.AsyncMock, return_value=None
    )

    credentials = {
        'token': 'xxx', 'client_id': '123', 'scopes': [],
        'authorization_endpoint': 'https://example.com/authorize',
        'token_endpoint': 'https://example.com./tokens',
        'scope': '',
        'client_secret': 'xyz'
    }

    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    assert await client.token_refresh(server, credentials) is None

    exchange_refresh_token.assert_called_once()


async def test_client_authenticate():
    credentials_manager = MockCredentialsManager()
    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    client = MCPClient(credentials_manager=credentials_manager)
    assert await client.authenticate(server) is None
