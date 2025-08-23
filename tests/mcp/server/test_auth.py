import httpx
import jwt
import pydantic
import pytest
from starlette.exceptions import HTTPException


from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from jotsu.mcp.client import OAuth2AuthorizationCodeClient
from jotsu.mcp.local.cache import AsyncMemoryCache
from jotsu.mcp.server import ThirdPartyAuthServerProvider, AsyncClientManager, utils
from mcp.server.auth.provider import AuthorizationParams, AuthorizationCode


class MockAsyncClientManager(AsyncClientManager):
    def __init__(self):
        self._client = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._client.get(client_id)

    async def save_client(self, client: OAuthClientInformationFull | None) -> None:
        self._client[client.client_id] = client


@pytest.fixture(name='provider', scope='function')
def provider_fixture():
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


async def test_auth(provider):
    client_info = OAuthClientInformationFull(
        client_id='abc',
        redirect_uris=[pydantic.AnyHttpUrl('https://localhost/redirect')],
    )

    await provider.register_client(client_info)
    assert (await provider.get_client(client_id='abc')).client_id == 'abc'


async def test_auth_register_error(provider, mocker):
    logger_exception = mocker.patch('jotsu.mcp.server.auth.logger.exception')
    client_info = OAuthClientInformationFull(
        client_id='abc',
        redirect_uris=[pydantic.AnyHttpUrl('https://localhost/redirect')],
    )
    mocker.patch.object(provider.client_manager, 'save_client', side_effect=Exception)

    with pytest.raises(Exception):
        await provider.register_client(client_info)
    logger_exception.assert_called_once()


async def test_auth_authorize(provider, mocker):
    client_info = OAuthClientInformationFull(
        client_id='abc',
        redirect_uris=[pydantic.AnyHttpUrl('https://localhost/redirect')],
    )

    params = AuthorizationParams(
        state='xxx',
        scopes=[],
        redirect_uri=client_info.redirect_uris[0],
        code_challenge='abc',
        redirect_uri_provided_explicitly=False
    )

    url = await provider.authorize(client_info, params=params)
    assert url


async def test_auth_load_authorization_code(provider, client_info):
    params = AuthorizationParams(
        state='xxx',
        scopes=[],
        redirect_uri=client_info.redirect_uris[0],
        code_challenge='abc',
        redirect_uri_provided_explicitly=False
    )

    await utils.cache_set(provider.cache, '123', params)

    res = await provider.load_authorization_code(client_info, '123')
    assert res.code == '123'


async def test_auth_exchange_authorization_code(provider, client_info, authorization_code, mocker):
    mocked_oauth = mocker.patch.object(provider.oauth, 'exchange_authorization_code', new_callable=mocker.AsyncMock)
    mocked_oauth.return_value = OAuthToken(access_token='abc')

    res = await provider.exchange_authorization_code(client_info, authorization_code=authorization_code)
    assert res.access_token != 'abc'


async def test_auth_exchange_authorization_code_status_error(provider, client_info, authorization_code, mocker):
    logger_error = mocker.patch('jotsu.mcp.server.auth.logger.error')
    mocked_oauth = mocker.patch.object(provider.oauth, 'exchange_authorization_code', new_callable=mocker.AsyncMock)

    response = mocker.Mock()
    response.status_code = 400
    mocked_oauth.side_effect = httpx.HTTPStatusError('status error', request=mocker.Mock(), response=response)

    with pytest.raises(HTTPException) as e:
        await provider.exchange_authorization_code(client_info, authorization_code=authorization_code)

    assert e.value.status_code == 500
    logger_error.assert_called_once()


async def test_auth_exchange_authorization_code_exception(provider, client_info, authorization_code, mocker):
    logger_exception = mocker.patch('jotsu.mcp.server.auth.logger.exception')
    mocked_oauth = mocker.patch.object(provider.oauth, 'exchange_authorization_code', new_callable=mocker.AsyncMock)

    response = mocker.Mock()
    response.status_code = 400
    mocked_oauth.side_effect = Exception()

    with pytest.raises(HTTPException) as e:
        await provider.exchange_authorization_code(client_info, authorization_code=authorization_code)

    assert e.value.status_code == 500
    logger_exception.assert_called_once()


async def test_auth_load_refresh_token(provider, client_info):
    payload = {
        'token': '123',
        'client_id': client_info.client_id,
        'scopes': [],
        'expires_at': None
    }

    refresh_token = jwt.encode(payload, provider.secret_key, algorithm='HS256')

    res = await provider.load_refresh_token(client_info, refresh_token)
    assert res.token == '123'


async def test_auth_load_refresh_token_decode_error(provider, client_info):
    payload = {
        'token': '123',
        'client_id': client_info.client_id,
        'scopes': [],
        'expires_at': None
    }

    refresh_token = jwt.encode(payload, 'XXX', algorithm='HS256')

    res = await provider.load_refresh_token(client_info, refresh_token)
    assert res is None


async def test_auth_exchange_refresh_token(provider, client_info, mocker):
    mock_oauth = mocker.patch.object(provider.oauth, 'exchange_refresh_token', new_callable=mocker.AsyncMock)
    mock_oauth.return_value = None

    payload = {
        'token': '123',
        'client_id': client_info.client_id,
        'scopes': [],
        'expires_at': None
    }

    refresh_token = await provider.load_refresh_token(
        client_info, jwt.encode(payload, provider.secret_key, algorithm='HS256')
    )

    res = await provider.exchange_refresh_token(client_info, refresh_token, [])
    assert res is None


async def test_auth_load_access_token(provider, client_info):
    payload = {
        'token': '123',
        'client_id': client_info.client_id,
        'scopes': [],
        'expires_at': None
    }

    access_token = jwt.encode(payload, provider.secret_key, algorithm='HS256')

    res = await provider.load_access_token(access_token)
    assert res.token == '123'


async def test_auth_load_access_token_decode_error(provider, client_info):
    payload = {
        'token': '123',
        'client_id': client_info.client_id,
        'scopes': [],
        'expires_at': None
    }

    access_token = jwt.encode(payload, 'XXX', algorithm='HS256')

    res = await provider.load_access_token(access_token)
    assert res is None


async def test_auth_revoke_token(provider, mocker):
    # not implemented
    assert await provider.revoke_token(mocker.Mock()) is None
