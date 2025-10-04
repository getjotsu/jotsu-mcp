import pydantic

from mcp.server.auth.provider import AuthorizationParams

from jotsu.mcp.server.routes import RegistrationHandler, RedirectHandler


async def test_route_redirect(third_party_provider, mocker):
    params = AuthorizationParams(
        state='xxx',
        scopes=[],
        redirect_uri=pydantic.AnyHttpUrl('https://example.com/redirect'),
        code_challenge='abc',
        redirect_uri_provided_explicitly=False
    )

    # noinspection PyTestUnpassedFixture
    await third_party_provider.cache.set('123', params.model_dump_json())

    request = mocker.Mock()
    request.query_params = {'state': '123', 'code': '345'}

    handler = RedirectHandler(third_party_provider)
    res = await handler.handle(request)
    assert res


async def test_route_registration(pass_thru_provider, mocker):
    save_client = mocker.patch.object(pass_thru_provider.client_manager, 'save_client', new_callable=mocker.AsyncMock)

    handler = RegistrationHandler(pass_thru_provider)

    request = mocker.AsyncMock()
    request.form.return_value = {
        'client_id': '123',
        'client_secret': 'xyz',
        'redirect_uris': ['http://localhost/redirect']
    }

    response = await handler.handle(request)
    assert response.status_code == 200
    save_client.assert_called_once()


async def test_route_registration_422(pass_thru_provider, mocker):
    handler = RegistrationHandler(pass_thru_provider)

    form = mocker.Mock()
    form.get.return_value = ''
    form.getlist.return_value = []

    request = mocker.AsyncMock()
    request.form.return_value = form

    response = await handler.handle(request)
    assert response.status_code == 422
