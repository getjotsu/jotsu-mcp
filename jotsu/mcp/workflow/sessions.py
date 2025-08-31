import typing

from jotsu.mcp.client import MCPClient
from jotsu.mcp.client.client import MCPClientSession
from jotsu.mcp.types import Workflow, WorkflowServer


class WorkflowSessionManager:
    def __init__(self, workflow: Workflow, *, client: MCPClient):
        self._sessions: typing.Dict[str, MCPClientSession] = {}
        self._workflow = workflow
        self._client = client

    @property
    def workflow(self) -> Workflow:
        return self._workflow

    async def get_session(self, server: WorkflowServer):
        if server.id not in self._sessions:
            session = await self._client.session(server).__aenter__()
            await session.load()
            self._sessions[server.id] = session
        return self._sessions[server.id]

    async def close(self):
        for session in self._sessions.values():
            await session.__aexit__(None, None, None)
