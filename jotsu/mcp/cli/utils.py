import asyncio
import functools
from contextlib import asynccontextmanager
from ulid import ULID

from jotsu.mcp.local import LocalMCPClient
from jotsu.mcp.types import WorkflowServer


CREDENTIALS = 'credentials'


def async_cmd(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        coro = f(*args, **kwargs)
        if asyncio.iscoroutine(coro):
            return asyncio.run(coro)
        raise TypeError(f'Expected coroutine, got {type(coro)}')

    return wrapper


@asynccontextmanager
async def client_session(ctx, server: WorkflowServer):
    client = LocalMCPClient(credentials_manager=ctx.obj[CREDENTIALS])
    async with client.session(server) as session:
        yield session


def ulid():
    return str(ULID()).lower()
