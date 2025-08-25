import typing

from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata


# The reference implementation doesn't support sending client_id/client_secret via basic auth
# https://github.com/modelcontextprotocol/python-sdk/blob/eaf7cf41d5c1d3bcfd4416494ab5dc62b9c17a4a/src/mcp/shared/auth.py#L47  # noqa
class BasicAuthMixin:
    token_endpoint_auth_method: typing.Literal[
        'none', 'client_secret_post', 'client_secret_basic'
    ] = 'client_secret_post'


class OAuthClientMetadataWithBasicAuth(BasicAuthMixin, OAuthClientMetadata):
    ...


class OAuthClientInformationFullWithBasicAuth(BasicAuthMixin, OAuthClientInformationFull):
    ...
