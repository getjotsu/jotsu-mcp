from urllib.parse import urlparse, urlunparse


def server_url(path: str, *, url: str) -> str:
    # noinspection HttpUrlsUsage
    if path.startswith('http://') or path.startswith('https://'):
        return path

    parsed = urlparse(url)
    parsed = parsed._replace(path=path, query='', fragment='')
    return str(urlunparse(parsed))
