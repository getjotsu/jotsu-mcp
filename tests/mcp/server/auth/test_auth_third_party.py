import httpx
import jwt
import pydantic
import pytest
from starlette.exceptions import HTTPException


from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from jotsu.mcp.server import utils
from mcp.server.auth.provider import AuthorizationParams


async def test_auth_third_party(third_party_provider):
    client_info = OAuthClientInformationFull(
        client_id='abc',
        redirect_uris=[pydantic.AnyHttpUrl('https://localhost/redirect')],
    )

    await third_party_provider.register_client(client_info)
    assert (await third_party_provider.get_client(client_id='abc')).client_id == 'abc'


async def test_auth_third_party_register_error(third_party_provider, mocker):
    logger_exception = mocker.patch('jotsu.mcp.server.auth.third_party.logger.exception')
    client_info = OAuthClientInformationFull(
        client_id='abc',
        redirect_uris=[pydantic.AnyHttpUrl('https://localhost/redirect')],
    )
    mocker.patch.object(third_party_provider.client_manager, 'save_client', side_effect=Exception)

    with pytest.raises(Exception):
        await third_party_provider.register_client(client_info)
    logger_exception.assert_called_once()


async def test_auth_third_party_authorize(third_party_provider):
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

    url = await third_party_provider.authorize(client_info, params=params)
    assert url


async def test_auth_third_party_load_authorization_code(third_party_provider, client_info):
    params = AuthorizationParams(
        state='xxx',
        scopes=[],
        redirect_uri=client_info.redirect_uris[0],
        code_challenge='abc',
        redirect_uri_provided_explicitly=False
    )

    # noinspection PyTestUnpassedFixture
    await utils.cache_set(third_party_provider.cache, '123', params)

    res = await third_party_provider.load_authorization_code(client_info, '123')
    assert res.code == '123'


async def test_auth_third_party_exchange_authorization_code(
        third_party_provider, client_info, authorization_code, mocker
):
    mocked_oauth = mocker.patch.object(
        third_party_provider.oauth, 'exchange_authorization_code', new_callable=mocker.AsyncMock
    )
    mocked_oauth.return_value = OAuthToken(access_token='abc')

    res = await third_party_provider.exchange_authorization_code(client_info, authorization_code=authorization_code)
    assert res.access_token != 'abc'


async def test_auth_third_party_exchange_authorization_code_status_error(
        third_party_provider, client_info, authorization_code, mocker
):
    logger_error = mocker.patch('jotsu.mcp.server.auth.base.logger.error')
    mocked_oauth = mocker.patch.object(
        third_party_provider.oauth, 'exchange_authorization_code', new_callable=mocker.AsyncMock
    )

    response = mocker.Mock()
    response.status_code = 400
    mocked_oauth.side_effect = httpx.HTTPStatusError('status error', request=mocker.Mock(), response=response)

    with pytest.raises(HTTPException) as e:
        await third_party_provider.exchange_authorization_code(client_info, authorization_code=authorization_code)

    assert e.value.status_code == 500
    logger_error.assert_called_once()


async def test_auth_third_party_exchange_authorization_code_exception(
        third_party_provider, client_info, authorization_code, mocker
):
    logger_exception = mocker.patch('jotsu.mcp.server.auth.base.logger.exception')
    mocked_oauth = mocker.patch.object(
        third_party_provider.oauth, 'exchange_authorization_code', new_callable=mocker.AsyncMock
    )

    response = mocker.Mock()
    response.status_code = 400
    mocked_oauth.side_effect = Exception()

    with pytest.raises(HTTPException) as e:
        await third_party_provider.exchange_authorization_code(client_info, authorization_code=authorization_code)

    assert e.value.status_code == 500
    logger_exception.assert_called_once()


async def test_auth_third_party_load_refresh_token(third_party_provider, client_info):
    payload = {
        'token': '123',
        'client_id': client_info.client_id,
        'scopes': [],
        'expires_at': None
    }

    refresh_token = jwt.encode(payload, third_party_provider.secret_key, algorithm='HS256')

    res = await third_party_provider.load_refresh_token(client_info, refresh_token)
    assert res.token == '123'


async def test_auth_third_party_load_refresh_token_decode_error(third_party_provider, client_info):
    payload = {
        'token': '123',
        'client_id': client_info.client_id,
        'scopes': [],
        'expires_at': None
    }

    refresh_token = jwt.encode(payload, 'XXX', algorithm='HS256')

    res = await third_party_provider.load_refresh_token(client_info, refresh_token)
    assert res is None


async def test_auth_third_party_exchange_refresh_token(third_party_provider, client_info, mocker):
    mock_oauth = mocker.patch.object(
        third_party_provider.oauth, 'exchange_refresh_token', new_callable=mocker.AsyncMock
    )
    mock_oauth.return_value = None

    payload = {
        'token': '123',
        'client_id': client_info.client_id,
        'scopes': [],
        'expires_at': None
    }

    refresh_token = await third_party_provider.load_refresh_token(
        client_info, jwt.encode(payload, third_party_provider.secret_key, algorithm='HS256')
    )

    res = await third_party_provider.exchange_refresh_token(client_info, refresh_token, [])
    assert res is None


async def test_auth_third_party_load_access_token(third_party_provider, client_info):
    payload = {
        'token': '123',
        'client_id': client_info.client_id,
        'scopes': [],
        'expires_at': None
    }

    access_token = jwt.encode(payload, third_party_provider.secret_key, algorithm='HS256')

    res = await third_party_provider.load_access_token(access_token)
    assert res.token == '123'


async def test_auth_third_party_load_access_token_decode_error(third_party_provider, client_info):
    payload = {
        'token': '123',
        'client_id': client_info.client_id,
        'scopes': [],
        'expires_at': None
    }

    access_token = jwt.encode(payload, 'XXX', algorithm='HS256')

    res = await third_party_provider.load_access_token(access_token)
    assert res is None


async def test_auth_third_party_revoke_token(third_party_provider, mocker):
    # not implemented
    assert await third_party_provider.revoke_token(mocker.Mock()) is None
