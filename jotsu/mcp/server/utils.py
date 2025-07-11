import json
import typing
from pydantic import BaseModel

from .cache import AsyncCache

T = typing.TypeVar('T', bound=BaseModel)


# Get as a pydantic type.
async def cache_get(cache: AsyncCache, key: str, cls: typing.Type[T]) -> T | None:
    value = await cache.get(key)
    return cls(**json.loads(value)) if value else None


async def cache_set(cache: AsyncCache, key: str, value: BaseModel, expires_in: int | None = None) -> None:
    await cache.set(key, value=value.model_dump_json(), expires_in=expires_in)
