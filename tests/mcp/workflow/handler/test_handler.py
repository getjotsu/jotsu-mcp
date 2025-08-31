import pydantic
import pytest

from mcp.types import (
    ReadResourceResult, TextResourceContents, BlobResourceContents,
    GetPromptResult, PromptMessage, TextContent, ImageContent,
    CallToolResult, Tool
)

from jotsu.mcp.types.exceptions import JotsuException
from jotsu.mcp.types.models import WorkflowMCPNode, WorkflowLoopNode, WorkflowSwitchNode, WorkflowFunctionNode, \
    WorkflowTransformNode, WorkflowTransform, WorkflowServer
from jotsu.mcp.types.rules import GreaterThanEqualRule, LessThanRule
from jotsu.mcp.workflow import WorkflowEngine
from jotsu.mcp.workflow.handler import WorkflowHandler


async def test_handler_resource(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode.model_create(name='data://resource', type='resource', server_id='test')

    handler = WorkflowHandler(engine=engine)

    contents = [
        TextResourceContents(mimeType=None, text='xxx', uri=pydantic.AnyUrl('data://resource'))
    ]

    session = mocker.AsyncMock()
    session.read_resource.return_value = ReadResourceResult(contents=contents)

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    assert await handler.handle_resource({}, sessions=sessions, node=node) == {'data://resource': 'xxx'}


async def test_handler_resource_json(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode.model_create(name='data://resource', type='resource', server_id='test')

    handler = WorkflowHandler(engine=engine)

    contents = [
        TextResourceContents(mimeType='application/json', text='{"foo":"baz"}', uri=pydantic.AnyUrl('data://resource'))
    ]

    session = mocker.AsyncMock()
    session.read_resource.return_value = ReadResourceResult(contents=contents)

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    assert await handler.handle_resource({}, sessions=sessions, node=node) == {'foo': 'baz'}


async def test_handler_resource_json_member(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='data://resource', type='resource', server_id='test', member='foo')

    handler = WorkflowHandler(engine=engine)

    contents = [
        TextResourceContents(mimeType='application/json', text='{"bar":"baz"}', uri=pydantic.AnyUrl('data://resource'))
    ]

    session = mocker.AsyncMock()
    session.read_resource.return_value = ReadResourceResult(contents=contents)

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    assert await handler.handle_resource({}, sessions=sessions, node=node) == {'foo': {'bar': 'baz'}}


async def test_handler_resource_not_found(mocker):
    logger_warning = mocker.patch('jotsu.mcp.workflow.handler.handler.logger.warning')

    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='data://resource', type='resource', server_id='test')

    handler = WorkflowHandler(engine=engine)

    contents = [
        BlobResourceContents(mimeType=None, blob='', uri=pydantic.AnyUrl('data://resource'))
    ]

    session = mocker.AsyncMock()
    session.read_resource.return_value = ReadResourceResult(contents=contents)

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    assert await handler.handle_resource({}, sessions=sessions, node=node) == {}
    logger_warning.assert_called_once()


async def test_handler_prompt(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='prompt', type='prompt', server_id='test')

    handler = WorkflowHandler(engine=engine)

    messages = [
        PromptMessage(role='user', content=TextContent(type='text', text='xxx'))
    ]

    session = mocker.AsyncMock()
    session.get_prompt.return_value = GetPromptResult(messages=messages)

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    assert await handler.handle_prompt({}, sessions=sessions, node=node) == {'prompt': 'xxx'}


async def test_handler_prompt_bad_type(mocker):
    logger_warning = mocker.patch('jotsu.mcp.workflow.handler.handler.logger.warning')

    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='prompt', type='prompt', server_id='test')

    handler = WorkflowHandler(engine=engine)

    messages = [
        PromptMessage(role='user', content=ImageContent(type='image', data='xxx', mimeType='image/png'))
    ]

    session = mocker.AsyncMock()
    session.get_prompt.return_value = GetPromptResult(messages=messages)

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    assert await handler.handle_prompt({}, sessions=sessions, node=node) == {}
    logger_warning.assert_called_once()


async def test_handler_tool(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    input_schema = {
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string'
            }
        },
        'required': ['name']
    }

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test-tool', inputSchema=input_schema)])
    session.call_tool.return_value = CallToolResult(isError=False, content=[TextContent(type='text', text='xxx')])

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    res = await handler.handle_tool({'name': 'foo'}, sessions=sessions, node=node)
    assert res == {'name': 'foo', 'test-tool': 'xxx'}


async def test_handler_tool_structured_content(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test-tool', inputSchema={})])

    call_tool_result = CallToolResult(
        isError=False, content=[TextContent(type='text', text='{"a": "b"}')]
    )
    call_tool_result.structuredContent = {'a': 'b'}
    session.call_tool.return_value = call_tool_result

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    res = await handler.handle_tool({}, sessions=sessions, node=node)
    assert res == {'a': 'b'}


async def test_handler_tool_structured_content_member(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test', member='foo')

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test-tool', inputSchema={})])

    call_tool_result = CallToolResult(
        isError=False, content=[TextContent(type='text', text='{"a": "b"}')]
    )
    call_tool_result.structuredContent = {'a': 'b'}
    session.call_tool.return_value = call_tool_result

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    res = await handler.handle_tool({}, sessions=sessions, node=node)
    assert res == {'foo': {'a': 'b'}}


async def test_handler_tool_schema_validation_error(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    input_schema = {
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string'
            }
        },
        'required': ['name']
    }

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test-tool', inputSchema=input_schema)])

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    with pytest.raises(JotsuException):
        await handler.handle_tool({}, sessions=sessions, node=node)


async def test_handler_tool_error(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test-tool', inputSchema={})])
    session.call_tool.return_value = CallToolResult(isError=True, content=[TextContent(type='text', text='error?')])

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    with pytest.raises(JotsuException):
        await handler.handle_tool({}, sessions=sessions, node=node)


async def test_handler_tool_get_none(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[])

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    with pytest.raises(JotsuException):
        await handler.handle_tool({}, sessions=sessions, node=node)


async def test_handler_tool_bad_type(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)

    content = ImageContent(type='image', data='xxx', mimeType='image/png')

    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test-tool', inputSchema={})])
    session.call_tool.return_value = CallToolResult(isError=False, content=[content])

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    assert await handler.handle_tool({}, sessions=sessions, node=node) == {}


async def test_handler_bad_session(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)
    sessions = mocker.AsyncMock()
    sessions.get_session.return_value = None

    with pytest.raises(JotsuException):
        await handler.handle_tool({}, sessions=sessions, node=node)


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


async def test_handler_function_empty():
    engine = WorkflowEngine([])
    node = WorkflowFunctionNode(
        id='1', name='test-function',
        function='return [data, None]'
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_function({'x': {'y': 3}}, node=node)
    assert [x.model_dump() for x in results] == []


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
