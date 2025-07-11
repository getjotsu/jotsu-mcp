import pytest

from jotsu.mcp.client import MCPClient


@pytest.mark.asyncio
async def test_credentials():
    client = MCPClient()
    await client.credentials.store('123', {'access_token': 'xxx'})
    assert (await client.credentials.load('123'))['access_token'] == 'xxx'
