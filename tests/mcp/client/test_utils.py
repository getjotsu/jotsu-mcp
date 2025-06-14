import httpx

from jotsu.mcp.client import utils


def test_server_url():
    assert utils.server_url('https://example.com', url='https://localhost') == 'https://example.com'


def test_is_httpx_401_exception():
    req = httpx.Request('GET', 'https://example.com')
    res = httpx.Response(401)
    e = BaseExceptionGroup('error', [httpx.HTTPStatusError('xxx', request=req, response=res)])
    assert utils.is_httpx_401_exception(e)

    res = httpx.Response(200)
    e = BaseExceptionGroup('error', [httpx.HTTPStatusError('xxx', request=req, response=res)])
    assert utils.is_httpx_401_exception(e) is False
