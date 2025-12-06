import pytest
from pydantic import AnyHttpUrl

from jotsu.mcp.types import Workflow, WorkflowNode, WorkflowServer, WorkflowToolNode


def test_workflow():
    workflow = Workflow.model_create()
    assert workflow.id


def test_workflow_node():
    node = WorkflowNode.model_create(name='test', type='test')
    assert node.id


def test_workflow_server():
    server = WorkflowServer.model_create(url='https://example.com')
    assert server.id


def test_mcp_node_validation():
    with pytest.raises(ValueError):
        WorkflowToolNode(id='test', server_id='1', url=AnyHttpUrl('https://example.com'))


def test_mcp_node_warning(mocker):
    logger_warning = mocker.patch('jotsu.mcp.types.models.logger.warning')
    WorkflowToolNode(id='test', server_id='1', headers={'Authorization': 'Bearer XXX'})
    logger_warning.assert_called_once()
