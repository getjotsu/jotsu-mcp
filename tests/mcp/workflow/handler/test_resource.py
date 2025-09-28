import pydantic

from mcp.types import ReadResourceResult, TextResourceContents, BlobResourceContents

from jotsu.mcp.types import WorkflowResourceNode
from jotsu.mcp.types.models import WorkflowServer
from jotsu.mcp.workflow import WorkflowEngine
from jotsu.mcp.workflow.handler import WorkflowHandler


async def test_handler_resource(mocker):
    engine = WorkflowEngine([])
    node = WorkflowResourceNode.model_create(
        name='data://resource', uri='data://resource', type='resource', server_id='test'
    )

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
    node = WorkflowResourceNode.model_create(
        name='data://resource', uri='data://resource', type='resource', server_id='test'
    )

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
    node = WorkflowResourceNode(
        id='1', name='data://resource', uri=pydantic.AnyUrl('data://resource'),
        type='resource', server_id='test', member='foo'
    )

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
    logger_warning = mocker.patch('jotsu.mcp.workflow.handler.resources.logger.warning')

    engine = WorkflowEngine([])
    node = WorkflowResourceNode(
        id='1', name='data://resource', uri=pydantic.AnyUrl('data://resource'), type='resource', server_id='test'
    )

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
