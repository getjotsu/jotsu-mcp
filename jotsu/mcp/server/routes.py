import logging

from mcp.server.auth.provider import AuthorizationParams

from starlette.requests import Request
from starlette.responses import Response, RedirectResponse

from .cache import AsyncCache
from . import utils

logger = logging.getLogger(__name__)


def get_redirect_uri(*, url: str, code: str | None, state: str):
    url = f'{url}?state={state}'
    if code:
        url += f'&code={code}'
    return url


# See: https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization#2-2-example%3A-authorization-code-grant  # noqa
# Handles 'Redirect to callback URL with auth code'
# We add a custom route so that the same redirect can always be used in the oauth2 setup,
# regardless of client.
async def redirect_route(request: Request, *, cache: AsyncCache) -> Response:
    """ This is the route that the third-party auth server redirects back to on the
    MCP Server after authorization is complete. """

    logger.debug('redirect: %s', str(request.query_params))
    params = await utils.cache_get(cache, request.query_params['state'], AuthorizationParams)
    await cache.delete(request.query_params['state'])
    await utils.cache_set(cache, request.query_params['code'], params)

    url = get_redirect_uri(url=str(params.redirect_uri), code=request.query_params.get('code'), state=params.state)
    return RedirectResponse(url=url)
