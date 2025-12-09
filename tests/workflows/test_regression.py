from copy import deepcopy

from mcp.client.session import ClientSession
from mcp.types import CallToolResult, TextContent

from jotsu.mcp.types import Workflow
from jotsu.mcp.workflow import WorkflowEngine
from tests.workflows.utils import load_workflow


async def test_pagination_error(mocker):
    mocker.patch.object(ClientSession, 'call_tool', side_effect=[
        CallToolResult(
            content=[],
            structuredContent={
                'cursor': 'MTA=',
                'items': [
                    {'id': '0', 'value': 0}, {'id': '1', 'value': 1}, {'id': '2', 'value': 2}, {'id': '3', 'value': 3}
                ]
            }
        ),
        CallToolResult(
            content=[TextContent(text='ERROR!', type='text')],
            isError=True
        ),
    ])

    workflow = load_workflow('pagination')

    engine = WorkflowEngine([Workflow(**workflow)])
    trace = [deepcopy(x) async for x in engine.run_workflow('pagination')]
    assert trace[len(trace) - 1]['action'] == 'workflow-failed'
