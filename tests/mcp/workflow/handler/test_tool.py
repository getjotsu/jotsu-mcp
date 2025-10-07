import pytest

from mcp.types import TextContent, ImageContent, CallToolResult, Tool

from jotsu.mcp.types import WorkflowToolNode, WorkflowServer
from jotsu.mcp.types.exceptions import JotsuException
from jotsu.mcp.workflow import WorkflowEngine
from jotsu.mcp.workflow.handler import WorkflowHandler


async def test_handler_tool(mocker):
    engine = WorkflowEngine([])
    node = WorkflowToolNode(id='1', name='test-tool', tool_name='test_tool', type='tool', server_id='test')

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
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test_tool', inputSchema=input_schema)])
    session.call_tool.return_value = CallToolResult(isError=False, content=[TextContent(type='text', text='xxx')])

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    res = await handler.handle_tool({'name': 'foo'}, sessions=sessions, node=node)
    assert res == {'name': 'foo', 'test_tool': 'xxx'}


async def test_handler_tool_structured_content(mocker):
    engine = WorkflowEngine([])
    node = WorkflowToolNode(id='1', name='test-tool', tool_name='test_tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test_tool', inputSchema={})])

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
    node = WorkflowToolNode(
        id='1', name='test-tool', tool_name='test_tool', type='tool', server_id='test', member='foo'
    )

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test_tool', inputSchema={})])

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
    node = WorkflowToolNode(id='1', name='test-tool', tool_name='test_tool', type='tool', server_id='test')

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
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test_tool', inputSchema=input_schema)])

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    with pytest.raises(JotsuException):
        await handler.handle_tool({}, sessions=sessions, node=node)


async def test_handler_tool_error(mocker):
    engine = WorkflowEngine([])
    node = WorkflowToolNode(id='1', name='test-tool', tool_name='test_tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test_tool', inputSchema={})])
    session.call_tool.return_value = CallToolResult(isError=True, content=[TextContent(type='text', text='error?')])

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    with pytest.raises(JotsuException):
        await handler.handle_tool({}, sessions=sessions, node=node)


async def test_handler_tool_get_none(mocker):
    engine = WorkflowEngine([])
    node = WorkflowToolNode(id='1', name='test-tool', tool_name='test_tool', type='tool', server_id='test')

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
    node = WorkflowToolNode(id='1', name='test-tool', tool_name='test_tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)

    content = ImageContent(type='image', data='xxx', mimeType='image/png')

    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test_tool', inputSchema={})])
    session.call_tool.return_value = CallToolResult(isError=False, content=[content])

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    assert await handler.handle_tool({}, sessions=sessions, node=node) == {}


async def test_handler_tool_structured_output(mocker):
    engine = WorkflowEngine([])
    node = WorkflowToolNode(
        id='1', name='test-tool', tool_name='test_tool', type='tool', server_id='test', structured_output=True
    )

    input_schema = {
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string'
            },
            'kwargs': {
                'type': 'object'
            }
        },
        'required': ['name', 'kwargs']
    }

    handler = WorkflowHandler(engine=engine)
    session = mocker.AsyncMock()
    session.list_tools.return_value = mocker.Mock(tools=[Tool(name='test_tool', inputSchema=input_schema)])
    session.call_tool.return_value = CallToolResult(
        isError=False, content=[TextContent(type='text', text='[{"foo": "baz"}]')]
    )

    sessions = mocker.AsyncMock()
    sessions.workflow.servers = [WorkflowServer.model_create(id='test', url='https://testserver/mcp/')]
    sessions.get_session.return_value = session

    res = await handler.handle_tool({'name': 'test'}, sessions=sessions, node=node)
    assert res == {'name': 'test', 'foo': 'baz'}
