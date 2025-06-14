# OAuthAuthorizationServerProvider has no access to request.session - it might not exist if
# SessionMiddleware isn't used - so we have to pass a 'cache' parameter to the OAuth constructor.
# The cache parameter doesn't have a firm type, but it's async dict-like and specifically just uses
# get, set and delete.
class AsyncCache:
    """KV store of session information keyed by the opaque 'state' or 'code' value from OAuth2."""
    async def get(self, key: str) -> str | None:
        ...

    async def set(self, key: str, value: str, expires_in: int | None = None):
        ...

    async def delete(self, key: str):
        ...
