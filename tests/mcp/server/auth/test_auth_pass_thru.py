import jwt
import pydantic
import pytest

from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.server.auth.provider import AuthorizationParams


async def test_auth_pass_thru_register_client(pass_thru_provider):
    with pytest.raises(NotImplementedError):
        client_info = OAuthClientInformationFull(
            client_id='abc',
            redirect_uris=[pydantic.AnyHttpUrl('https://localhost/redirect')],
        )

        await pass_thru_provider.register_client(client_info)


async def test_auth_pass_thru_get_client(pass_thru_provider):
    client_info = OAuthClientInformationFull(
        client_id='abc',
        redirect_uris=[pydantic.AnyHttpUrl('https://localhost/redirect')],
    )

    await pass_thru_provider.client_manager.save_client(client_info)
    assert await pass_thru_provider.get_client(client_info.client_id) == client_info


async def test_auth_pass_thru_authorize(pass_thru_provider):
    client_info = OAuthClientInformationFull(
        client_id='abc',
        redirect_uris=[pydantic.AnyHttpUrl('https://localhost/redirect')],
        scope='readonly'
    )

    params = AuthorizationParams(
        state='xxx',
        scopes=[],
        redirect_uri=client_info.redirect_uris[0],
        code_challenge='abc',
        redirect_uri_provided_explicitly=False
    )

    url = await pass_thru_provider.authorize(client_info, params=params)
    assert url


async def test_auth_pass_thru_exchange_authorization_code(pass_thru_provider, client_info, authorization_code, mocker):
    mocker.patch.object(
        pass_thru_provider, '_exchange_authorization_code',
        new_callable=mocker.AsyncMock, return_value=OAuthToken(access_token='token')
    )

    res = await pass_thru_provider.exchange_authorization_code(client_info, authorization_code=authorization_code)
    assert res.access_token == 'token'


async def test_auth_pass_thru_exchange_refresh_token(pass_thru_provider, client_info, mocker):
    payload = {
        'token': '123',
        'client_id': client_info.client_id,
        'scopes': [],
        'expires_at': None
    }
    mocker.patch.object(
        pass_thru_provider, '_exchange_refresh_token',
        new_callable=mocker.AsyncMock, return_value=None
    )

    refresh_token = await pass_thru_provider.load_refresh_token(
        client_info, jwt.encode(payload, pass_thru_provider.secret_key, algorithm='HS256')
    )

    res = await pass_thru_provider.exchange_refresh_token(client_info, refresh_token, [])
    assert res is None


async def test_auth_pass_thru_revoke_token(pass_thru_provider, mocker):
    # not implemented
    with pytest.raises(NotImplementedError):
        assert await pass_thru_provider.revoke_token(mocker.Mock()) is None
