import typing
from urllib.parse import urlparse, urlunparse

import httpx


def server_url(path: str, *, url: str) -> str:
    # noinspection HttpUrlsUsage
    if path.startswith('http://') or path.startswith('https://'):
        return path

    parsed = urlparse(url)
    parsed = parsed._replace(path=path, query='', fragment='')
    return str(urlunparse(parsed))


def is_httpx_401_exception(e: BaseExceptionGroup) -> bool:
    if e.exceptions and isinstance(e.exceptions[0], httpx.HTTPStatusError):
        status_error = typing.cast(httpx.HTTPStatusError, e.exceptions[0])
        if status_error.response.status_code == 401:
            return True
    return False
