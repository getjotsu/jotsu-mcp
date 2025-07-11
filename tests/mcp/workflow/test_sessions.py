from jotsu.mcp.local import LocalMCPClient
from jotsu.mcp.types import Workflow
from jotsu.mcp.workflow.sessions import WorkflowSessionManager


def test_sessions():
    workflow = Workflow(id='test-workflow', name='Test')
    sessions = WorkflowSessionManager(workflow=workflow, client=LocalMCPClient())
    assert sessions.get('123') is None
