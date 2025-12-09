from copy import deepcopy

from jotsu.mcp.types import Workflow
from jotsu.mcp.workflow import WorkflowEngine
from tests.workflows.utils import load_workflow


async def test_workflow_loop():
    workflow = load_workflow('loop')

    engine = WorkflowEngine([Workflow(**workflow)])
    trace = [deepcopy(x) async for x in engine.run_workflow('loop')]
    assert trace[len(trace) - 1]['action'] == 'workflow-end'

    result = trace[len(trace) - 1]['result']
    assert result['values'] == ['1', '2', '3']


async def test_workflow_post():
    workflow = load_workflow('post')

    engine = WorkflowEngine([Workflow(**workflow)])
    trace = [deepcopy(x) async for x in engine.run_workflow('post')]
    assert trace[len(trace) - 1]['action'] == 'workflow-end'

    result = trace[len(trace) - 1]['result']
    assert result['value'] == 2


async def test_workflow_complete():
    workflow = load_workflow('complete')

    engine = WorkflowEngine([Workflow(**workflow)])
    trace = [deepcopy(x) async for x in engine.run_workflow('complete')]
    assert trace[len(trace) - 1]['action'] == 'workflow-end'

    result = trace[len(trace) - 1]['result']
    assert result['status'] == 'ok'


async def test_workflow_pagination():
    workflow = load_workflow('pagination')

    engine = WorkflowEngine([Workflow(**workflow)])
    trace = [deepcopy(x) async for x in engine.run_workflow('pagination')]
    assert trace[len(trace) - 1]['action'] == 'workflow-end'

    result = trace[len(trace) - 1]['result']
    assert result['sum'] == 153
