import pydantic
import pytest

from mcp.server.auth.provider import AuthorizationParams

from jotsu.mcp.local.cache import AsyncMemoryCache
from jotsu.mcp.server import redirect_route


@pytest.mark.anyio
async def test_route_redirect_route(mocker):
    params = AuthorizationParams(
        state='xxx',
        scopes=[],
        redirect_uri=pydantic.AnyHttpUrl('https://example.com/redirect'),
        code_challenge='abc',
        redirect_uri_provided_explicitly=False
    )

    cache = AsyncMemoryCache()
    await cache.set('123', params.model_dump_json())

    request = mocker.Mock()
    request.query_params = {'state': '123', 'code': '345'}

    res = await redirect_route(request, cache=cache)
    assert res
