from jotsu.mcp.types import Workflow, WorkflowNode, WorkflowServer


def test_workflow():
    workflow = Workflow()
    assert workflow.id


def test_workflow_node():
    node = WorkflowNode(name='test', type='test')
    assert node.id


def test_workflow_server():
    server = WorkflowServer(url='https://example.com')
    assert server.id
