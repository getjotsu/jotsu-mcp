from mcp.types import GetPromptResult, PromptMessage, TextContent, ImageContent

from jotsu.mcp.types import WorkflowPromptNode, WorkflowServer
from jotsu.mcp.workflow import WorkflowEngine
from jotsu.mcp.workflow.handler import WorkflowHandler


async def test_handler_prompt(mocker):
    engine = WorkflowEngine([])
    node = WorkflowPromptNode(id='1', name='prompt', prompt_name='prompt', type='prompt', server_id='test')

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
    logger_warning = mocker.patch('jotsu.mcp.workflow.handler.prompts.logger.warning')

    engine = WorkflowEngine([])
    node = WorkflowPromptNode(id='1', name='prompt', prompt_name='prompt', type='prompt', server_id='test')

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
