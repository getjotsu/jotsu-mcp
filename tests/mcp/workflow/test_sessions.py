import pydantic

from jotsu.mcp.local import LocalMCPClient
from jotsu.mcp.types import Workflow, WorkflowServer
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
    assert await sessions.get_session(server) == mocked_session

    await sessions.close()
