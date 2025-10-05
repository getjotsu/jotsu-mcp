import logging

import pydantic
from mcp.server.auth.errors import stringify_pydantic_error
from mcp.server.auth.handlers.register import RegistrationErrorResponse
from mcp.server.auth.json_response import PydanticJSONResponse
from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl

from starlette.requests import Request
from starlette.responses import Response, RedirectResponse, JSONResponse

from .auth.base import BaseAuthServerProvider
from .cache import AsyncCache
from . import utils, AsyncClientManager, PassThruAuthServerProvider

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


class RedirectHandler:
    def __init__(self, provider: BaseAuthServerProvider):
        self._provider = provider

    async def handle(self, request: Request):
        return await redirect_route(request, cache=self._provider.cache)


class RegistrationRequest(pydantic.BaseModel):
    client_id: str
    client_secret: str
    redirect_uris: list[AnyUrl] = pydantic.Field(..., min_length=1)


# This is NOT for dynamic client registration but instead for 'static' client registration where
# the user adds a client_id/client_secret and redirect uris via a form POST request.
class StaticRegistrationHandler:
    CAPABILITY = 'registration.static'
    _client_manager: AsyncClientManager

    def __init__(self, provider: PassThruAuthServerProvider):
        self._provider = provider

    async def handle(self, request: Request):
        try:
            # Parse request body as JSON
            body = await request.json()
            client_metadata = RegistrationRequest.model_validate(body)

            # Scope validation is handled below
        except pydantic.ValidationError as validation_error:
            return PydanticJSONResponse(
                content=RegistrationErrorResponse(
                    error='invalid_client_metadata',
                    error_description=stringify_pydantic_error(validation_error),
                ),
                status_code=422,
            )

        client = OAuthClientInformationFull(
            **client_metadata.model_dump(),
            scope=self._provider.scope
        )
        await self._provider.client_manager.save_client(client)
        return JSONResponse(
            status_code=200,
            content=client.model_dump(mode='json'),
            headers={'Cache-Control': 'no-store'},
        )
