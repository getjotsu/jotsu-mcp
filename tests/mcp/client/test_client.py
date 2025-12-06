from contextlib import asynccontextmanager

import pytest
import pydantic
import httpx
from mcp import McpError, ErrorData

from mcp.shared.auth import OAuthToken

from jotsu.mcp.client import MCPClient
from jotsu.mcp.client.client import MCPClientSession, split_scopes
from jotsu.mcp.client.credentials import CredentialsManager
from jotsu.mcp.types import WorkflowServer


class MockCredentialsManager(CredentialsManager):
    async def load(self, server_id: str) -> dict | None:
        return {
            'access_token': 'xxx',
            'refresh_token': 'xxx', 'client_id': '123',
            'authorization_endpoint': 'https://example.com/authorize',
            'token_endpoint': 'https://example.com./tokens',
            'scope': '',
            'client_secret': 'xyz'
        }


async def test_client():
    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))

    client = MCPClient()
    async with client.session(server) as session:
        assert session.server
        result = await session.call_tool('greet', {'name': 'World'})
        assert result.isError is False


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


async def test_client_auth_force(mocker):

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

    client = MCPClient()
    mocker.patch.object(client, '_connect', new=mock_connect)
    authenticate = mocker.patch.object(client, 'authenticate', return_value='xxx', new_callable=mocker.AsyncMock)

    async with client.session(server, authenticate=True) as session:
        assert await session.call_tool('greet', {'name': 'World'})

    assert authenticate.call_count == 2


async def test_client_error(mocker):
    req = httpx.Request('GET', 'https://example.com')
    res = httpx.Response(500)
    e = BaseExceptionGroup('error', [httpx.HTTPStatusError('xxx', request=req, response=res)])

    @asynccontextmanager
    async def mock_connect(*_args, **_kwargs):
        raise e
        yield  # noqa

    credentials_manager = MockCredentialsManager()
    client = MCPClient(credentials_manager=credentials_manager)
    mocker.patch.object(client, '_connect', new=mock_connect)

    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    with pytest.raises(BaseExceptionGroup):
        async with client.session(server):
            ...


def test_client_headers():
    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    server.headers['Authorization'] = 'Bot 123'  # like discord

    client = MCPClient()
    headers = client.headers(server, headers=httpx.Headers())
    assert headers['authorization'] == 'Bot 123'


async def test_refresh_token(mocker):
    token = OAuthToken(access_token='xxx')

    credentials_manager = MockCredentialsManager()
    client = MCPClient(credentials_manager=credentials_manager)
    exchange_refresh_token = mocker.patch(
        'jotsu.mcp.client.OAuth2AuthorizationCodeClient.exchange_refresh_token',
        new_callable=mocker.AsyncMock, return_value=token
    )

    credentials = {
        'refresh_token': 'xxx', 'client_id': '123',
        'authorization_endpoint': 'https://example.com/authorize',
        'token_endpoint': 'https://example.com./tokens',
        'scope': 'doc.read doc.write',
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
        'refresh_token': 'xxx', 'client_id': '123',
        'authorization_endpoint': 'https://example.com/authorize',
        'token_endpoint': 'https://example.com./tokens',
        'scope': '',
        'client_secret': 'xyz'
    }

    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    assert await client.token_refresh(server, credentials) is None

    exchange_refresh_token.assert_called_once()


async def test_client_authenticate(mocker):
    credentials_manager = MockCredentialsManager()
    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    client = MCPClient(credentials_manager=credentials_manager)

    token = OAuthToken(access_token='xxx')
    exchange_refresh_token = mocker.patch(
        'jotsu.mcp.client.OAuth2AuthorizationCodeClient.exchange_refresh_token',
        new_callable=mocker.AsyncMock, return_value=token
    )

    assert await client.authenticate(server) == 'xxx'
    exchange_refresh_token.assert_called_once()


async def test_client_authenticate_none(mocker):
    credentials_manager = MockCredentialsManager()
    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    client = MCPClient(credentials_manager=credentials_manager)

    exchange_refresh_token = mocker.patch(
        'jotsu.mcp.client.OAuth2AuthorizationCodeClient.exchange_refresh_token',
        new_callable=mocker.AsyncMock, return_value=None
    )

    assert await client.authenticate(server) is None
    exchange_refresh_token.assert_called_once()


async def test_client_session(mocker):
    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    session = MCPClientSession(
        read_stream=mocker.Mock(), write_stream=mocker.Mock(), client=mocker.Mock(), server=server
    )

    list_tools = mocker.patch.object(session, 'list_tools', new_callable=mocker.AsyncMock)
    list_tools.return_value = mocker.Mock()
    list_tools.return_value.tools = []

    list_resources = mocker.patch.object(session, 'list_resources', new_callable=mocker.AsyncMock)
    list_resources.return_value = mocker.Mock()
    list_resources.return_value.resources = []

    list_prompts = mocker.patch.object(session, 'list_prompts', new_callable=mocker.AsyncMock)
    list_prompts.return_value = mocker.Mock()
    list_prompts.return_value.prompts = []

    server = await session.load()
    assert server

    list_tools.assert_called_once()
    list_resources.assert_called_once()
    list_prompts.assert_called_once()


async def test_client_session_error(mocker):
    logger_debug = mocker.patch('jotsu.mcp.client.client.logger.debug',)

    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    session = MCPClientSession(
        read_stream=mocker.Mock(), write_stream=mocker.Mock(), client=mocker.Mock(), server=server
    )

    list_tools = mocker.patch.object(
        session, 'list_tools', new_callable=mocker.AsyncMock,
        side_effect=McpError(ErrorData(code=-1, message='error'))
    )
    list_tools.return_value = mocker.Mock()
    list_tools.return_value.tools = []

    list_resources = mocker.patch.object(
        session, 'list_resources', new_callable=mocker.AsyncMock,
        side_effect=McpError(ErrorData(code=-1, message='error'))
    )
    list_resources.return_value = mocker.Mock()
    list_resources.return_value.resources = []

    list_prompts = mocker.patch.object(
        session, 'list_prompts', new_callable=mocker.AsyncMock,
        side_effect=McpError(ErrorData(code=-1, message='error'))
    )
    list_prompts.return_value = mocker.Mock()
    list_prompts.return_value.prompts = []

    server = await session.load()
    assert server

    list_tools.assert_called_once()
    list_resources.assert_called_once()
    list_prompts.assert_called_once()

    assert logger_debug.call_count == 3


def test_split_scopes():
    scopes = split_scopes('a      b   c')
    assert scopes == ['a', 'b', 'c']

    scopes = split_scopes('ab c')
    assert scopes == ['ab', 'c']

    scopes = split_scopes('a')
    assert scopes == ['a']

    assert split_scopes('') == []
