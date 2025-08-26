import os

from jotsu.mcp.types import Workflow
from jotsu.mcp.types.models import WorkflowOpenAINode
from jotsu.mcp.workflow import WorkflowEngine


async def test_handler_openai(mocker):
    from openai.types.responses import Response, ResponseOutputMessage, ResponseOutputText, ResponseUsage
    from openai.types.responses.response_usage import InputTokensDetails, OutputTokensDetails

    os.environ['OPENAI_API_KEY'] = 'sk_key'

    content = ResponseOutputText(type='output_text', text='xxx', annotations=[])
    output = ResponseOutputMessage(id='a', type='message', role='assistant', content=[content], status='completed')

    response = Response(
        id='1',
        model='gpt-5',
        object='response',
        output=[output],
        parallel_tool_calls=False,
        tool_choice='none',
        tools=[],
        created_at=0,
        usage=ResponseUsage(
            input_tokens=0, input_tokens_details=InputTokensDetails(cached_tokens=0),
            output_tokens=0, output_tokens_details=OutputTokensDetails(reasoning_tokens=0),
            total_tokens=0
        )
    )

    workflow = Workflow(id='workflow')
    engine = WorkflowEngine([workflow])

    openai_client = engine.handler.openai_client
    openai_client_create = mocker.patch.object(
        openai_client.responses, 'create', new_callable=mocker.AsyncMock
    )
    openai_client_create.return_value = response

    node = WorkflowOpenAINode(
        id='a', name='chatgpt', messages=[],
        model='gpt-5', system='foo', member='baz'
    )

    result = await engine.handler.handle_openai(
        {'prompt': 'What?'},
        action_id='x', workflow=workflow, node=node, usage=[]
    )
    assert result['baz'] == 'xxx'
    openai_client_create.assert_called_once()
    os.environ.pop('OPENAI_API_KEY')


async def test_handler_openai_schema(mocker):
    from openai.types.responses import Response, ResponseOutputMessage, ResponseOutputText, ResponseUsage
    from openai.types.responses.response_usage import InputTokensDetails, OutputTokensDetails

    os.environ['OPENAI_API_KEY'] = 'sk_key'

    content = ResponseOutputText(type='output_text', text='{"foo": "baz"}', annotations=[])
    output = ResponseOutputMessage(id='a', type='message', role='assistant', content=[content], status='completed')

    response = Response(
        id='1',
        model='gpt-5',
        object='response',
        output=[output],
        parallel_tool_calls=False,
        tool_choice='none',
        tools=[],
        created_at=0,
        usage=ResponseUsage(
            input_tokens=0, input_tokens_details=InputTokensDetails(cached_tokens=0),
            output_tokens=0, output_tokens_details=OutputTokensDetails(reasoning_tokens=0),
            total_tokens=0
        )
    )

    workflow = Workflow(id='workflow')
    engine = WorkflowEngine([workflow])

    openai_client = engine.handler.openai_client
    openai_client_create = mocker.patch.object(
        openai_client.responses, 'create', new_callable=mocker.AsyncMock
    )
    openai_client_create.return_value = response

    node = WorkflowOpenAINode(
        id='a', name='chatgpt', messages=[], model='gpt-5',
        json_schema={'properties': {}}, include_message_in_output=False
    )

    result = await engine.handler.handle_openai(
        {}, action_id='x', workflow=workflow, node=node, usage=[]
    )
    assert result['foo'] == 'baz'
    openai_client_create.assert_called_once()
    os.environ.pop('OPENAI_API_KEY')
