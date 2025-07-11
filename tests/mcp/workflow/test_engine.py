from contextlib import asynccontextmanager

import pydantic
import pytest

from jotsu.mcp.types import Workflow, WorkflowServer
from jotsu.mcp.types.models import WorkflowNode, WorkflowToolNode, WorkflowResourceNode, WorkflowPromptNode
from jotsu.mcp.workflow import WorkflowEngine
from jotsu.mcp.workflow.handler import WorkflowHandler


@pytest.mark.anyio
async def test_engine():
    workflow = Workflow(id='test', name='Test')
    engine = WorkflowEngine([workflow])

    trace = [x async for x in engine.run_workflow('Test')]
    assert len(trace) == 2
    assert trace[0]['action'] == 'workflow-start'
    assert trace[1]['action'] == 'workflow-end'


class MockHandler(WorkflowHandler):
    @staticmethod
    async def handle_tool(data: dict, **_kwargs) -> dict:
        return data

    @staticmethod
    async def handle_prompt(data: dict, **_kwargs) -> dict:
        return data

    @staticmethod
    async def handle_resource(data: dict, **_kwargs) -> dict:
        return data

    @staticmethod
    async def handle_other(data: dict, **_kwargs) -> dict:
        return data


@pytest.mark.anyio
async def test_engine_workflow(mocker):

    @asynccontextmanager
    async def context(*_args, **_kwargs):
        mocked_server = mocker.Mock()
        mocker.patch.object(mocked_server, 'load', new_callable=mocker.AsyncMock)
        yield {'test-server': mocked_server}

    mocker.patch('jotsu.mcp.workflow.engine.WorkflowSessionManager.context', context)

    workflow = Workflow(id='test-workflow', name='Test', start_node_id='1')

    workflow.servers.append(WorkflowServer(id='test-server', url=pydantic.AnyHttpUrl('https://example.com/mcp/')))

    workflow.nodes.append(WorkflowToolNode(id='1', name='tool', server_id='test-server', edges=['2']))
    workflow.nodes.append(WorkflowResourceNode(id='2', name='resource', server_id='test-server', edges=['3']))
    workflow.nodes.append(WorkflowPromptNode(id='3', name='prompt', server_id='test-server', edges=['4']))
    workflow.nodes.append(WorkflowNode(id='4', name='other', type='other'))

    engine = WorkflowEngine([workflow], handler_cls=MockHandler)

    trace = [x async for x in engine.run_workflow('test-workflow', data={'foo': 'bar'})]
    assert len(trace) == 10   # 2 per node + workflow start/end


@pytest.mark.anyio
async def test_engine_default_handler():
    workflow = Workflow(id='test-workflow', name='Test', start_node_id='1')
    workflow.nodes.append(WorkflowNode(id='1', name='missing', type='unknown'))

    engine = WorkflowEngine([workflow], handler_cls=MockHandler)

    trace = [x async for x in engine.run_workflow('test-workflow')]
    assert len(trace) == 3
    assert trace[1]['action'] == 'default'


@pytest.mark.anyio
async def test_engine_workflow_not_found(mocker):
    logger_error = mocker.patch('jotsu.mcp.workflow.engine.logger.error')
    engine = WorkflowEngine([], handler_cls=MockHandler)

    with pytest.raises(ValueError):
        async for _ in engine.run_workflow('test-workflow'):
            ...
    logger_error.assert_called_once()
