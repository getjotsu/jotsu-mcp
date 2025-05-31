from jotsu.mcp.client import utils


def test_server_url():
    assert utils.server_url('https://example.com', url='https://localhost') == 'https://example.com'
