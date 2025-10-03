import json
import os

from anyio import open_file
from mcp.shared.auth import OAuthClientInformationFull

from jotsu.mcp.server import AsyncClientManager
from .encryption import HAVE_CRYPTOGRAPHY


class LocalClientManager(AsyncClientManager):

    def __init__(self, path: str = None):
        path = path if path else '~/.jotsu'
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.exists(path):
            assert os.path.isdir(path)

        path = os.path.join(path, 'clients')
        os.makedirs(path, exist_ok=True)
        self._path = path

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        path = os.path.join(self._path, client_id)
        try:
            async with await open_file(path, 'r') as fp:
                return OAuthClientInformationFull(**json.loads(await fp.read()))
        except (OSError, IOError, ValueError):
            pass
        return None

    async def save_client(self, client: OAuthClientInformationFull):
        path = os.path.join(self._path, client.client_id)
        async with await open_file(path, 'w') as fp:
            await fp.write(client.model_dump_json())


if HAVE_CRYPTOGRAPHY:
    from .encryption import Encryption

    class LocalEncryptedClientManager(LocalClientManager):

        def __init__(self, key: str, *, path: str = None):
            super().__init__(path)
            self._encryption = Encryption(key)

        async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
            path = os.path.join(self._path, client_id)
            try:
                async with await open_file(path, 'rb') as fp:
                    obj = json.loads(self._encryption.decrypt(await fp.read()))
                    return OAuthClientInformationFull(**obj)
            except (OSError, IOError, ValueError):
                pass
            return None

        async def save_client(self, client: OAuthClientInformationFull):
            path = os.path.join(self._path, client.client_id)
            async with await open_file(path, 'wb') as fp:
                await fp.write(self._encryption.encrypt(client.model_dump_json()))
