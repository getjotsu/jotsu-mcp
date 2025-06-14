from contextlib import asynccontextmanager

import pydantic
import pytest

from mcp.shared.memory import create_connected_server_and_client_session

from jotsu.mcp.common import Workflow, WorkflowServer
from jotsu.mcp.workflow import WorkflowEngine


@pytest.fixture(scope='function', name='engine')
async def engine_fixture():
    return WorkflowEngine([])


@asynccontextmanager
async def client_session(engine: WorkflowEngine):
    # noinspection PyProtectedMember
    async with create_connected_server_and_client_session(engine._mcp_server) as session:
        yield session


@pytest.mark.anyio
async def test_workflow_server():
    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    workflow = Workflow(id='hello', servers=[server])
    engine = WorkflowEngine([workflow])

    async with client_session(engine) as session:
        result = await session.call_tool('workflow', {'name': 'hello'})
        assert result.isError is False
        assert len(result.content) == 1


@pytest.mark.anyio
async def test_workflow_server_by_name():
    server = WorkflowServer(id='hello', url=pydantic.AnyHttpUrl('https://hello.mcp.jotsu.com/mcp/'))
    workflow = Workflow(id='hello', name='Hello', servers=[server])
    engine = WorkflowEngine([workflow])

    async with client_session(engine) as session:
        result = await session.call_tool('workflow', {'name': 'Hello'})
        assert result.isError is False
        assert len(result.content) == 1


@pytest.mark.anyio
async def test_workflow_server_not_found(engine):
    async with client_session(engine) as session:
        result = await session.call_tool('workflow', {'name': 'hello'})
        assert result.isError
