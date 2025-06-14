import asyncio
import functools


def async_cmd(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        coro = f(*args, **kwargs)
        if asyncio.iscoroutine(coro):
            return asyncio.run(coro)
        raise TypeError(f'Expected coroutine, got {type(coro)}')

    return wrapper
