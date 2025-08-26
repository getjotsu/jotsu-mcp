from jotsu.mcp.types import Workflow
from jotsu.mcp.types.models import WorkflowCloudflareNode
from jotsu.mcp.workflow import WorkflowEngine


async def test_handler_cloudflare(mocker):
    response = {
        'response': 'xxx',
        'usage': {'input_tokens': 0, 'output_tokens': 0}
    }

    workflow = Workflow(id='workflow')
    engine = WorkflowEngine([workflow])

    cloudflare_client = engine.handler.cloudflare_client
    cloudflare_client_run = mocker.patch.object(
        cloudflare_client.ai, 'run', new_callable=mocker.AsyncMock
    )
    cloudflare_client_run.return_value = response

    node = WorkflowCloudflareNode(
        id='a', name='cf', messages=[],
        model='meta', system='foo', member='baz'
    )

    result = await engine.handler.handle_cloudflare(
        {'prompt': 'What?'},
        action_id='x', workflow=workflow, node=node, usage=[]
    )
    assert result['baz'] == 'xxx'
    cloudflare_client_run.assert_called_once()


async def test_handler_cloudflare_schema(mocker):
    response = {
        'response': '{"foo": "baz"}',
        'usage': {'input_tokens': 0, 'output_tokens': 0}
    }

    workflow = Workflow(id='workflow')
    engine = WorkflowEngine([workflow])

    cloudflare_client = engine.handler.cloudflare_client
    cloudflare_client_run = mocker.patch.object(
        cloudflare_client.ai, 'run', new_callable=mocker.AsyncMock
    )
    cloudflare_client_run.return_value = response

    node = WorkflowCloudflareNode(
        id='a', name='cf', messages=[],
        model='meta', system='foo', use_json_schema=True,
    )

    result = await engine.handler.handle_cloudflare(
        {}, action_id='x', workflow=workflow, node=node, usage=[]
    )
    assert result['foo'] == 'baz'
    cloudflare_client_run.assert_called_once()
