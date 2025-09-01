import pydantic

from jotsu.mcp.types import Workflow
from jotsu.mcp.types.models import WorkflowAnthropicNode, WorkflowServer
from jotsu.mcp.workflow import WorkflowEngine


async def test_handler_anthropic(mocker):
    from anthropic.types.beta.beta_message import BetaMessage
    from anthropic.types.beta.beta_text_block import BetaTextBlock
    from anthropic.types.beta.beta_usage import BetaUsage

    message = BetaMessage(
        id='1',
        content=[BetaTextBlock(text='XXX', type='text'), BetaTextBlock(text='YYY', type='text')],
        model='claude', role='assistant', type='message',
        usage=BetaUsage(input_tokens=0, output_tokens=0)
    )

    workflow = Workflow(id='workflow')
    engine = WorkflowEngine([workflow])

    anthropic_client = engine.handler.anthropic_client
    anthropic_client_create = mocker.patch.object(
        anthropic_client.beta.messages, 'create', new_callable=mocker.AsyncMock
    )
    anthropic_client_create.return_value = message

    node = WorkflowAnthropicNode(
        id='a', name='claude', messages=[],
        model='claude-2', system='foo'
    )

    result = await engine.handler.handle_anthropic(
        {'prompt': 'What?'},
        action_id='x', workflow=workflow, node=node, usage=[]
    )
    assert 'content' in result
    assert result['claude'] == 'XXX\nYYY'
    anthropic_client_create.assert_called_once()


async def test_handler_anthropic_schema(mocker):
    from anthropic.types.beta.beta_message import BetaMessage
    from anthropic.types.beta.beta_text_block import BetaTextBlock
    from anthropic.types.beta.beta_tool_use_block import BetaToolUseBlock
    from anthropic.types.beta.beta_usage import BetaUsage

    structured_output = {
        'foo': 'baz'
    }

    message = BetaMessage(
        id='1',
        content=[
            BetaTextBlock(text='XXX', type='text'),
            BetaToolUseBlock(id='123', input=structured_output, name='structured_output', type='tool_use')
        ],
        model='claude', role='assistant', type='message',
        usage=BetaUsage(input_tokens=0, output_tokens=0)
    )

    workflow = Workflow(id='workflow')
    engine = WorkflowEngine([workflow])
    anthropic_client = engine.handler.anthropic_client
    anthropic_client_create = mocker.patch.object(
        anthropic_client.beta.messages, 'create', new_callable=mocker.AsyncMock
    )
    anthropic_client_create.return_value = message

    node = WorkflowAnthropicNode(
        id='a', name='claude', messages=[],
        model='claude-2', json_schema={'must_not_be_empty': True},
        include_message_in_output=False
    )

    result = await engine.handler.handle_anthropic(
        {'prompt': 'What?'}, action_id='x', workflow=workflow, node=node, usage=[]
    )
    assert result['foo'] == 'baz'
    anthropic_client_create.assert_called_once()


async def test_handler_anthropic_servers(mocker):
    logger_warning = mocker.patch('jotsu.mcp.workflow.handler.anthropic.logger.warning')
    from anthropic.types.beta.beta_message import BetaMessage
    from anthropic.types.beta.beta_text_block import BetaTextBlock
    from anthropic.types.beta.beta_usage import BetaUsage

    message = BetaMessage(
        id='1',
        content=[
            BetaTextBlock(text='XXX', type='text'),
        ],
        model='claude', role='assistant', type='message',
        usage=BetaUsage(input_tokens=0, output_tokens=0)
    )

    server = WorkflowServer(
        id='server',
        url=pydantic.AnyHttpUrl('https://example.com/mcp/'),
        headers={'Authorization': 'Bearer xxx'}
    )
    workflow = Workflow(id='workflow', servers=[server])
    engine = WorkflowEngine([workflow])
    anthropic_client = engine.handler.anthropic_client
    anthropic_client_create = mocker.patch.object(
        anthropic_client.beta.messages, 'create', new_callable=mocker.AsyncMock
    )
    anthropic_client_create.return_value = message

    node = WorkflowAnthropicNode(
        id='a', name='claude', messages=[],
        model='claude-2', json_schema={'must_not_be_empty': True},
        servers=[server.id, 'foo']
    )

    result = await engine.handler.handle_anthropic(
        {'prompt': 'What?'}, action_id='x', workflow=workflow, node=node, usage=[]
    )
    assert 'content' in result
    anthropic_client_create.assert_called_once()
    logger_warning.assert_called_once()
