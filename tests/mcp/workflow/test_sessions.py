import pydantic
import pytest

from jotsu.mcp.local import LocalMCPClient
from jotsu.mcp.types import Workflow, WorkflowServer, WorkflowToolNode
from jotsu.mcp.workflow.sessions import WorkflowSessionManager


async def test_sessions(mocker):
    mocked_session = mocker.AsyncMock()
    mocked_session.load.return_value = None

    mocker.patch(
        'jotsu.mcp.client.client.MCPClientSession.__aenter__',
        new_callable=mocker.AsyncMock, return_value=mocked_session
    )

    server = WorkflowServer.model_create(url=pydantic.AnyHttpUrl('https://example.com/mcp/'))
    workflow = Workflow(id='test-workflow', name='Test', servers=[server])
    sessions = WorkflowSessionManager(workflow=workflow, client=LocalMCPClient())

    assert sessions.workflow == workflow
    assert await sessions.get_session(server.id) == mocked_session
    assert await sessions.get_session(server.id) == mocked_session  # cached version

    await sessions.close()


async def test_sessions_closed():
    server = WorkflowServer.model_create(url=pydantic.AnyHttpUrl('https://example.com/mcp/'))
    workflow = Workflow(id='test-workflow', name='Test', servers=[server])
    sessions = WorkflowSessionManager(workflow=workflow, client=LocalMCPClient())
    await sessions.close()
    with pytest.raises(RuntimeError):
        await sessions.get_session(server)
    await sessions.close()  # safely close again


async def test_sessions_different_task(mocker):
    mocked_session = mocker.AsyncMock()
    mocked_session.load.return_value = None

    mocker.patch(
        'jotsu.mcp.client.client.MCPClientSession.__aenter__',
        new_callable=mocker.AsyncMock, return_value=mocked_session
    )

    server = WorkflowServer.model_create(url=pydantic.AnyHttpUrl('https://example.com/mcp/'))
    workflow = Workflow(id='test-workflow', name='Test', servers=[server])
    sessions = WorkflowSessionManager(workflow=workflow, client=LocalMCPClient())
    assert await sessions.get_session(server.id)  # necessary to set the owner task

    mocker.patch('asyncio.current_task')
    with pytest.raises(RuntimeError):
        await sessions.close()


async def test_sessions_node(mocker):
    mocked_session = mocker.AsyncMock()
    mocked_session.load.return_value = None

    mocker.patch(
        'jotsu.mcp.client.client.MCPClientSession.__aenter__',
        new_callable=mocker.AsyncMock, return_value=mocked_session
    )

    node = WorkflowToolNode.model_create(url=pydantic.AnyHttpUrl('https://example.com/mcp/'))
    workflow = Workflow(id='test-workflow', name='Test', nodes=[node])
    sessions = WorkflowSessionManager(workflow=workflow, client=LocalMCPClient())

    assert sessions.workflow == workflow
    assert await sessions.get_session(node.id) == mocked_session

    await sessions.close()


async def test_sessions_not_found(mocker):
    workflow = Workflow(id='test-workflow', name='Test')
    sessions = WorkflowSessionManager(workflow=workflow, client=LocalMCPClient())

    with pytest.raises(RuntimeError):
        await sessions.get_session('123')
