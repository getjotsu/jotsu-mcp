import pydantic
import pytest

from mcp.types import (
    ReadResourceResult, TextResourceContents, BlobResourceContents,
    GetPromptResult, PromptMessage, TextContent, ImageContent,
    CallToolResult
)

from jotsu.mcp.types.exceptions import JotsuException
from jotsu.mcp.types.models import WorkflowMCPNode, WorkflowLoopNode, WorkflowSwitchNode, WorkflowFunctionNode, \
    WorkflowAnthropicNode, Workflow, WorkflowServer, WorkflowTransformNode, WorkflowTransform
from jotsu.mcp.types.rules import GreaterThanEqualRule, LessThanRule
from jotsu.mcp.workflow import WorkflowEngine
from jotsu.mcp.workflow.handler import WorkflowHandler


@pytest.mark.anyio
async def test_handler_resource(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='data://resource', type='resource', server_id='test')

    handler = WorkflowHandler(engine=engine)

    contents = [
        TextResourceContents(mimeType=None, text='xxx', uri=pydantic.AnyUrl('data://resource'))
    ]

    session = mocker.AsyncMock()
    session.read_resource.return_value = ReadResourceResult(contents=contents)

    sessions = mocker.Mock()
    sessions.get.return_value = session

    assert await handler.handle_resource({}, sessions=sessions, node=node) == {'data://resource': 'xxx'}


@pytest.mark.anyio
async def test_handler_resource_json(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='data://resource', type='resource', server_id='test')

    handler = WorkflowHandler(engine=engine)

    contents = [
        TextResourceContents(mimeType='application/json', text='{"foo":"baz"}', uri=pydantic.AnyUrl('data://resource'))
    ]

    session = mocker.AsyncMock()
    session.read_resource.return_value = ReadResourceResult(contents=contents)

    sessions = mocker.Mock()
    sessions.get.return_value = session

    assert await handler.handle_resource({}, sessions=sessions, node=node) == {'foo': 'baz'}


@pytest.mark.anyio
async def test_handler_resource_json_member(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='data://resource', type='resource', server_id='test', member='foo')

    handler = WorkflowHandler(engine=engine)

    contents = [
        TextResourceContents(mimeType='application/json', text='{"bar":"baz"}', uri=pydantic.AnyUrl('data://resource'))
    ]

    session = mocker.AsyncMock()
    session.read_resource.return_value = ReadResourceResult(contents=contents)

    sessions = mocker.Mock()
    sessions.get.return_value = session

    assert await handler.handle_resource({}, sessions=sessions, node=node) == {'foo': {'bar': 'baz'}}


@pytest.mark.anyio
async def test_handler_resource_not_found(mocker):
    logger_warning = mocker.patch('jotsu.mcp.workflow.handler.logger.warning')

    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='data://resource', type='resource', server_id='test')

    handler = WorkflowHandler(engine=engine)

    contents = [
        BlobResourceContents(mimeType=None, blob='', uri=pydantic.AnyUrl('data://resource'))
    ]

    session = mocker.AsyncMock()
    session.read_resource.return_value = ReadResourceResult(contents=contents)

    sessions = mocker.Mock()
    sessions.get.return_value = session

    assert await handler.handle_resource({}, sessions=sessions, node=node) == {}
    logger_warning.assert_called_once()


@pytest.mark.anyio
async def test_handler_prompt(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='prompt', type='prompt', server_id='test')

    handler = WorkflowHandler(engine=engine)

    messages = [
        PromptMessage(role='user', content=TextContent(type='text', text='xxx'))
    ]

    session = mocker.AsyncMock()
    session.get_prompt.return_value = GetPromptResult(messages=messages)

    sessions = mocker.Mock()
    sessions.get.return_value = session

    assert await handler.handle_prompt({}, sessions=sessions, node=node) == {'prompt': 'xxx'}


@pytest.mark.anyio
async def test_handler_prompt_bad_type(mocker):
    logger_warning = mocker.patch('jotsu.mcp.workflow.handler.logger.warning')

    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='prompt', type='prompt', server_id='test')

    handler = WorkflowHandler(engine=engine)

    messages = [
        PromptMessage(role='user', content=ImageContent(type='image', data='xxx', mimeType='image/png'))
    ]

    session = mocker.AsyncMock()
    session.get_prompt.return_value = GetPromptResult(messages=messages)

    sessions = mocker.Mock()
    sessions.get.return_value = session

    assert await handler.handle_prompt({}, sessions=sessions, node=node) == {}
    logger_warning.assert_called_once()


@pytest.mark.anyio
async def test_handler_tool(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.call_tool.return_value = CallToolResult(isError=False, content=[TextContent(type='text', text='xxx')])

    sessions = mocker.Mock()
    sessions.get.return_value = session

    assert await handler.handle_tool({}, sessions=sessions, node=node) == {'test-tool': 'xxx'}


@pytest.mark.anyio
async def test_handler_tool_error(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.call_tool.return_value = CallToolResult(isError=True, content=[TextContent(type='text', text='error?')])

    sessions = mocker.Mock()
    sessions.get.return_value = session

    with pytest.raises(JotsuException):
        await handler.handle_tool({}, sessions=sessions, node=node)


@pytest.mark.anyio
async def test_handler_tool_bad_type(mocker):
    logger_warning = mocker.patch('jotsu.mcp.workflow.handler.logger.warning')

    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)

    content = ImageContent(type='image', data='xxx', mimeType='image/png')

    session = mocker.AsyncMock()
    session.call_tool.return_value = CallToolResult(isError=False, content=[content])

    sessions = mocker.Mock()
    sessions.get.return_value = session

    assert await handler.handle_tool({}, sessions=sessions, node=node) == {}

    logger_warning.assert_called_once()


@pytest.mark.anyio
async def test_handler_bad_session(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)
    sessions = mocker.Mock()
    sessions.get.return_value = None

    with pytest.raises(JotsuException):
        await handler.handle_tool({}, sessions=sessions, node=node)


@pytest.mark.anyio
async def test_handler_switch():
    engine = WorkflowEngine([])
    node = WorkflowSwitchNode(
        id='1', name='test-switch', expr='x.y',
        rules=[LessThanRule(value=2), GreaterThanEqualRule(value=2)],
        edges=['e1', 'e2', 'e3']
    )

    handler = WorkflowHandler(engine=engine)

    results = await handler.handle_switch({'x': {'y': 3}}, node=node)

    expected = [
        {'edge': 'e2', 'data': {'x': {'y': 3}}},
        {'edge': 'e3', 'data': {'x': {'y': 3}}},
    ]

    assert [x.model_dump() for x in results] == expected


@pytest.mark.anyio
async def test_handler_loop():
    engine = WorkflowEngine([])
    node = WorkflowLoopNode(id='1', name='test-loop', expr='lines', edges=['e1', 'e2'])

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_loop({'lines': ['1', '2', '3']}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'lines': ['1', '2', '3'], '__each__': '1'}},
        {'edge': 'e1', 'data': {'lines': ['1', '2', '3'], '__each__': '2'}},
        {'edge': 'e1', 'data': {'lines': ['1', '2', '3'], '__each__': '3'}},
        {'edge': 'e2', 'data': {'lines': ['1', '2', '3'], '__each__': '1'}},
        {'edge': 'e2', 'data': {'lines': ['1', '2', '3'], '__each__': '2'}},
        {'edge': 'e2', 'data': {'lines': ['1', '2', '3'], '__each__': '3'}},
    ]

    assert [x.model_dump() for x in results] == expected


@pytest.mark.anyio
async def test_handler_loop_rules():
    engine = WorkflowEngine([])
    node = WorkflowLoopNode(
        id='1', name='test-loop', expr='lines',
        rules=[GreaterThanEqualRule(value=2)],
        edges=['e1', 'e2'])

    handler = WorkflowHandler(engine=engine)

    results = await handler.handle_loop({'lines': [1, 2, 3]}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'lines': [1, 2, 3], '__each__': 2}},
        {'edge': 'e1', 'data': {'lines': [1, 2, 3], '__each__': 3}},
        {'edge': 'e2', 'data': {'lines': [1, 2, 3], '__each__': 1}},
        {'edge': 'e2', 'data': {'lines': [1, 2, 3], '__each__': 2}},
        {'edge': 'e2', 'data': {'lines': [1, 2, 3], '__each__': 3}},
    ]

    assert [x.model_dump() for x in results] == expected


@pytest.mark.anyio
async def test_handler_function():
    engine = WorkflowEngine([])
    node = WorkflowFunctionNode(
        id='1', name='test-function',
        function='return data',
        edges=['e1', 'e2']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_function({'x': {'y': 3}}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'x': {'y': 3}}},
        {'edge': 'e2', 'data': {'x': {'y': 3}}},
    ]

    assert [x.model_dump() for x in results] == expected


@pytest.mark.anyio
async def test_handler_function_per_edge():
    engine = WorkflowEngine([])
    node = WorkflowFunctionNode(
        id='1', name='test-function',
        function='return [data, None]',
        edges=['e1', 'e2']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_function({'x': {'y': 3}}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'x': {'y': 3}}},
    ]

    assert [x.model_dump() for x in results] == expected


@pytest.mark.anyio
async def test_handler_function_empty():
    engine = WorkflowEngine([])
    node = WorkflowFunctionNode(
        id='1', name='test-function',
        function='return [data, None]'
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_function({'x': {'y': 3}}, node=node)
    assert [x.model_dump() for x in results] == []


@pytest.mark.anyio
async def test_handler_anthropic(mocker):
    from anthropic.types.beta.beta_message import BetaMessage
    from anthropic.types.beta.beta_text_block import BetaTextBlock
    from anthropic.types.beta.beta_usage import BetaUsage

    message = BetaMessage(
        id='1',
        content=[BetaTextBlock(text='XXX', type='text')],
        model='claude', role='assistant', type='message',
        usage=BetaUsage(input_tokens=0, output_tokens=0)
    )

    workflow = Workflow(id='workflow')
    engine = WorkflowEngine([workflow])

    anthropic_client = engine.anthropic_client
    anthropic_client_create = mocker.patch.object(
        anthropic_client.beta.messages, 'create', new_callable=mocker.AsyncMock
    )
    anthropic_client_create.return_value = message

    node = WorkflowAnthropicNode(
        id='a', name='claude', messages=[],
        model='claude-2', system='foo'
    )

    handler = WorkflowHandler(engine=engine)
    result = await handler.handle_anthropic({'prompt': 'What?'}, workflow=workflow, node=node, usage=[])
    assert 'content' in result
    anthropic_client_create.assert_called_once()


@pytest.mark.anyio
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
    anthropic_client = engine.anthropic_client
    anthropic_client_create = mocker.patch.object(
        anthropic_client.beta.messages, 'create', new_callable=mocker.AsyncMock
    )
    anthropic_client_create.return_value = message

    node = WorkflowAnthropicNode(
        id='a', name='claude', messages=[],
        model='claude-2', json_schema={'must_not_be_empty': True},
        include_message_in_output=False
    )

    handler = WorkflowHandler(engine=engine)
    result = await handler.handle_anthropic({'prompt': 'What?'}, workflow=workflow, node=node, usage=[])
    assert result['foo'] == 'baz'
    anthropic_client_create.assert_called_once()


@pytest.mark.anyio
async def test_handler_anthropic_servers(mocker):
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
        headers={'Authorization': 'xxx'}
    )
    workflow = Workflow(id='workflow', servers=[server])
    engine = WorkflowEngine([workflow])
    anthropic_client = engine.anthropic_client
    anthropic_client_create = mocker.patch.object(
        anthropic_client.beta.messages, 'create', new_callable=mocker.AsyncMock
    )
    anthropic_client_create.return_value = message

    node = WorkflowAnthropicNode(
        id='a', name='claude', messages=[],
        model='claude-2', json_schema={'must_not_be_empty': True},
    )

    handler = WorkflowHandler(engine=engine)
    result = await handler.handle_anthropic({'prompt': 'What?'}, workflow=workflow, node=node, usage=[])
    assert 'content' in result
    anthropic_client_create.assert_called_once()


async def test_handler_transform_move():
    engine = WorkflowEngine([])

    transform = WorkflowTransform(type='move', source='a', target='b')

    node = WorkflowTransformNode(
        id='1', name='test-transform',
        transforms=[transform],
        edges=['e1']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_transform({'a': 3}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'b': 3}}
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_transform_set():
    engine = WorkflowEngine([])

    transform = WorkflowTransform(type='set', source='$string(a * 2)', target='b.foo.bar')

    node = WorkflowTransformNode(
        id='1', name='test-transform',
        transforms=[transform],
        edges=['e1']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_transform({'a': 3}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'a': 3, 'b': {'foo': {'bar': '6'}}}}
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_transform_set_constant():
    engine = WorkflowEngine([])

    transform = WorkflowTransform(type='set', source='"c"', target='a.b')

    node = WorkflowTransformNode(
        id='1', name='test-transform',
        transforms=[transform],
        edges=['e1']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_transform({'a': {'b': 3}}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'a': {'b': 'c'}}}
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_transform_delete():
    engine = WorkflowEngine([])

    transform = WorkflowTransform(type='delete', source='a')

    node = WorkflowTransformNode(
        id='1', name='test-transform',
        transforms=[transform],
        edges=['e1']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_transform({'a': 3}, node=node)

    assert [x.model_dump() for x in results] == [{'edge': 'e1', 'data': {}}]
