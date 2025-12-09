import os
import json

from jotsu.mcp.client.credentials import CredentialsManager


class LocalCredentialsManager(CredentialsManager):
    """ Store credentials in the filesystem, using the user's home directory as a default.
    NOTE: these commands run synchronously to avoid having an aiofiles dependency.
    """
    def __init__(self, path: str = None, force: bool = False):
        path = path if path else '~/.jotsu'
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.exists(path):
            assert os.path.isdir(path)

        path = os.path.join(path, 'credentials')
        os.makedirs(path, exist_ok=True)
        self._path = path
        self._reload = set() if force else None

    async def load(self, server_id: str) -> dict | None:
        credentials = None
        if self._reload is None or server_id in self._reload:
            path = os.path.join(self._path, f'{server_id}.json')
            try:
                with open(path, 'r') as fp:
                    credentials = json.load(fp)
                    if self._reload is not None:
                        self._reload.add(server_id)
            except (OSError, IOError):
                pass
        return credentials

    async def store(self, server_id: str, credentials: dict) -> None:
        path = os.path.join(self._path, f'{server_id}.json')
        with open(path, 'w') as fp:
            json.dump(credentials, fp, indent=4)

    @staticmethod
    def _path(path: str | None):
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.exists(path):
            assert os.path.isdir(path)

        path = os.path.join(path, 'credentials')
        os.makedirs(path, exist_ok=True)
        return path
