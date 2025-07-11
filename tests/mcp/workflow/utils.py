from contextlib import asynccontextmanager

from mcp.shared.memory import create_connected_server_and_client_session

from jotsu.mcp.workflow import WorkflowEngine


@asynccontextmanager
async def client_session(engine: WorkflowEngine):
    # noinspection PyProtectedMember
    async with create_connected_server_and_client_session(engine._mcp_server) as session:
        yield session
