import pydantic
import pytest
import pkce
import httpx

from mcp.server.auth.provider import RefreshToken
from mcp.shared.auth import OAuthToken, OAuthClientInformationFull

from jotsu.mcp.client.oauth import OAuth2AuthorizationCodeClient


@pytest.fixture(scope='function', name='oauth_client')
def oauth_client_fixture():
    return OAuth2AuthorizationCodeClient(
        authorize_endpoint='https://example.com/authorize',
        token_endpoint='https://example.com/token',
        scope='scope',
        client_id='client_id',
        client_secret='client_secret'
    )


@pytest.mark.asyncio
async def test_oauth_authorize_info(oauth_client):
    state = oauth_client.generate_state()
    params = await oauth_client.authorize_info(redirect_uri='https://localhost', state=state)
    assert params.url == f'https://example.com/authorize?response_type=code&client_id=client_id&redirect_uri=https%3A%2F%2Flocalhost&scope=scope&state={state}'  # noqa


@pytest.mark.asyncio
async def test_oauth_exchange_authorization_token(oauth_client, mocker):
    token = OAuthToken(access_token='123')

    res = httpx.Response(200, json=token.model_dump(mode='json'))
    mocker.patch.object(res, 'raise_for_status')

    post = mocker.patch('httpx.AsyncClient.post', new=mocker.AsyncMock(return_value=res))

    result = await oauth_client.exchange_authorization_code(redirect_uri='https://localhost', code='xxx')
    assert result.access_token == token.access_token
    post.assert_called_once()


@pytest.mark.asyncio
async def test_oauth_exchange_authorization_token_pkce(oauth_client, mocker):
    code_verifier, _ = pkce.generate_pkce_pair()
    token = OAuthToken(access_token='123')

    res = httpx.Response(200, json=token.model_dump(mode='json'))
    mocker.patch.object(res, 'raise_for_status')

    post = mocker.patch('httpx.AsyncClient.post', new=mocker.AsyncMock(return_value=res))

    result = await oauth_client.exchange_authorization_code(
        redirect_uri='https://localhost', code='xxx', code_verifier=code_verifier
    )
    assert result.access_token == token.access_token
    post.assert_called_once()


@pytest.mark.asyncio
async def test_oauth_exchange_authorization_token_error(oauth_client, mocker):
    logger_warning = mocker.patch('jotsu.mcp.client.oauth.logger.warning')

    res = httpx.Response(400, request=httpx.Request(method='GET', url=oauth_client.token_endpoint))
    post = mocker.patch('httpx.AsyncClient.post', new=mocker.AsyncMock(return_value=res))

    with pytest.raises(httpx.HTTPStatusError) as e:
        await oauth_client.exchange_authorization_code(redirect_uri='https://localhost', code='xxx')

    assert e.value.response.status_code == 400
    post.assert_called_once()
    logger_warning.assert_called_once()


@pytest.mark.asyncio
async def test_oauth_exchange_refresh_token(oauth_client, mocker):
    token = OAuthToken(access_token='123')

    res = httpx.Response(200, json=token.model_dump(mode='json'))
    mocker.patch.object(res, 'raise_for_status')

    post = mocker.patch('httpx.AsyncClient.post', new=mocker.AsyncMock(return_value=res))

    refresh_token = RefreshToken(token='xyz', client_id=oauth_client.client_id, scopes=[])

    result = await oauth_client.exchange_refresh_token(refresh_token=refresh_token, scopes=[])
    assert result.access_token == token.access_token
    post.assert_called_once()


@pytest.mark.asyncio
async def test_oauth_exchange_refresh_token_failed(oauth_client, mocker):
    logger_warning = mocker.patch('jotsu.mcp.client.oauth.logger.warning')

    res = httpx.Response(400, request=httpx.Request(method='GET', url=oauth_client.token_endpoint))
    post = mocker.patch('httpx.AsyncClient.post', new=mocker.AsyncMock(return_value=res))

    refresh_token = RefreshToken(token='xyz', client_id=oauth_client.client_id, scopes=[])
    res = await oauth_client.exchange_refresh_token(refresh_token=refresh_token, scopes=[])
    assert res is None
    post.assert_called_once()
    logger_warning.assert_called_once()


@pytest.mark.asyncio
async def test_oauth_server_metadata_discovery(mocker):
    res = httpx.Response(200, json={
        'authorization_endpoint': 'http://127.0.0.1:8000/authorize',
        'token_endpoint': 'http://127.0.0.1:8000/token',
        'registration_endpoint': 'http://127.0.0.1:8000/register',
    })
    mocker.patch.object(res, 'raise_for_status')
    get = mocker.patch('httpx.AsyncClient.get', new=mocker.AsyncMock(return_value=res))

    server_metadata = await OAuth2AuthorizationCodeClient.server_metadata_discovery(
        base_url='http://127.0.0.1:8000/mcp/'
    )
    assert server_metadata
    get.assert_called_once()


@pytest.mark.asyncio
async def test_oauth_server_metadata_discovery_defaults(mocker):
    res = httpx.Response(
        404, request=httpx.Request(
            method='GET',
            url='https://example.com/.well-known/oauth-authorization-server'
        )
    )
    get = mocker.patch('httpx.AsyncClient.get', new=mocker.AsyncMock(return_value=res))

    server_metadata = await OAuth2AuthorizationCodeClient.server_metadata_discovery(
        base_url='http://127.0.0.1:8000/mcp/'
    )
    assert server_metadata
    get.assert_called_once()


@pytest.mark.asyncio
async def test_oauth_server_metadata_discovery_error(mocker):
    res = httpx.Response(
        400, request=httpx.Request(
            method='GET',
            url='https://example.com/.well-known/oauth-authorization-server'
        )
    )
    get = mocker.patch('httpx.AsyncClient.get', new=mocker.AsyncMock(return_value=res))

    with pytest.raises(httpx.HTTPStatusError):
        await OAuth2AuthorizationCodeClient.server_metadata_discovery(
            base_url='http://127.0.0.1:8000/mcp/'
        )
    get.assert_called_once()


@pytest.mark.asyncio
async def test_oauth_dynamic_client_registration(mocker):
    client_info = OAuthClientInformationFull(
        client_id='client_id',
        client_secret='client_secret',
        redirect_uris=[pydantic.AnyHttpUrl('http://localhost')],
    )
    res = httpx.Response(200, json=client_info.model_dump(mode='json'))
    mocker.patch.object(res, 'raise_for_status')
    post = mocker.patch('httpx.AsyncClient.post', new=mocker.AsyncMock(return_value=res))

    res = await OAuth2AuthorizationCodeClient.dynamic_client_registration(
        registration_endpoint='http://127.0.0.1:8000/register',
        redirect_uris=[str(redirect_uri) for redirect_uri in client_info.redirect_uris]
    )
    assert res
    post.assert_called_once()
