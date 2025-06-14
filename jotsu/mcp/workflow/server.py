import typing
from collections.abc import Mapping
from contextlib import asynccontextmanager, AsyncExitStack

import pydantic
from mcp.server.fastmcp import FastMCP
from mcp.types import Resource

from jotsu.mcp.common import Workflow
from jotsu.mcp.local import LocalMCPClient
from jotsu.mcp.client.client import MCPClient, MCPClientSession


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
        async with AsyncExitStack() as stack:
            self._sessions = {
                entry.id: await stack.enter_async_context(self._client.session(entry))
                for entry in self._workflow.servers
            }
            yield self


class WorkflowEngine(FastMCP):
    def __init__(
            self, workflows: Workflow | typing.List[Workflow], *args,
            client: typing.Optional[MCPClient] = None, **kwargs
    ):
        self._workflows = [workflows] if isinstance(workflows, Workflow) else workflows
        self._client = client if client else LocalMCPClient()

        super().__init__(*args, **kwargs)
        self.add_tool(self.run_workflow, name='workflow')

        for workflow in self._workflows:
            name = workflow.name if workflow.name else workflow.id
            resource = Resource(
                name=name,
                description=workflow.description,
                uri=pydantic.AnyUrl(f'workflow://{workflow.id}/'),
                mimeType='application/json'
            )
            self.add_resource(resource)

    def _get_workflow(self, name: str):
        for workflow in self._workflows:
            if workflow.id == name:
                return workflow
        for workflow in self._workflows:
            if workflow.name == name:
                return workflow
        return None

    async def run_workflow(self, name: str) -> str:
        workflow = self._get_workflow(name)
        if not workflow:
            raise ValueError(f'Workflow not found: {name}')

        result = []
        async with WorkflowSessionManager(workflow, client=self._client).context() as sessions:
            for session in sessions.values():  # type: MCPClientSession
                await session.load()
                result.append(session.server.model_dump_json())

        # currently it just tests the servers.
        return '\n'.join(result)
