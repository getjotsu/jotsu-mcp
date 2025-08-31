from jotsu.mcp.types import Workflow, WorkflowNode, WorkflowServer


def test_workflow():
    workflow = Workflow.model_create()
    assert workflow.id


def test_workflow_node():
    node = WorkflowNode.model_create(name='test', type='test')
    assert node.id


def test_workflow_server():
    server = WorkflowServer.model_create(url='https://example.com')
    assert server.id
