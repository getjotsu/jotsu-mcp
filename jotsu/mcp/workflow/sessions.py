import typing
from contextlib import asynccontextmanager, AsyncExitStack
from typing import Mapping

from jotsu.mcp.client import MCPClient
from jotsu.mcp.client.client import MCPClientSession
from jotsu.mcp.types import Workflow


class WorkflowSessionManager(Mapping):
    def __init__(self, workflow: Workflow, *, client: MCPClient):
        self._sessions: typing.Dict[str, MCPClientSession] = {}
        self._workflow = workflow
        self._client = client

    def __getitem__(self, key):
        return self._sessions[key]

    def __iter__(self):
        return iter(self._sessions)

    def __len__(self):
        return len(self._sessions)  # pragma: no cover

    @asynccontextmanager
    async def context(self):
        async with AsyncExitStack() as stack:  # noqa  // Incorrect warning about a meta class.
            self._sessions = {
                entry.id: await stack.enter_async_context(self._client.session(entry))
                for entry in self._workflow.servers
            }
            yield self
