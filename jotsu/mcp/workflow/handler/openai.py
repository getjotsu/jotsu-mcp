import logging
import typing

from jotsu.mcp.types import WorkflowModelUsage
from jotsu.mcp.types.models import WorkflowOpenAINode
from jotsu.mcp.workflow import utils
from .utils import get_messages, update_data_from_text, update_data_from_json

logger = logging.getLogger(__name__)


JSON_SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    'type': 'object',
    'properties': {}
}


class OpenAIMixin:

    @property
    def openai_client(self):
        if not hasattr(self, '_openai'):
            from openai import AsyncOpenAI
            setattr(self, '_openai', AsyncOpenAI())
        return getattr(self, '_openai')

    async def handle_openai(
            self, data: dict, *, action_id: str, node: WorkflowOpenAINode,
            usage: typing.List[WorkflowModelUsage], **_kwargs
    ):
        from openai import AsyncOpenAI
        from openai.types.responses import ResponseUsage, Response

        client: AsyncOpenAI = self.openai_client

        messages = get_messages(data, node.prompt)

        kwargs: dict = {}
        system = data.get('system', node.system)
        if system:
            # Responses API uses system messages instead of explicit kwarg
            messages.insert(0, {
                'role': 'system',
                'content': utils.pybars_render(system, data)
            })

        if node.json_schema:
            # OpenAI needs a schema for structured output or for production, a schema SHOULD be used.
            if node.use_json_schema or (node.use_json_schema is None):
                text = {
                    'format': {
                        'type': 'json_schema',
                        'name': 'structured_output',
                        'schema': node.json_schema
                    }
                }
                kwargs['text'] = text

        response: Response = await client.responses.create(
            model=node.model,
            input=messages,  # Responses API uses 'input' instead of 'messages'
            max_output_tokens=node.max_tokens,
            **kwargs
        )

        if response.usage:
            usage.append(
                WorkflowModelUsage(
                    ref_id=action_id,
                    model=node.model,
                    **typing.cast(ResponseUsage, response.usage).model_dump(mode='json')
                )
            )

        # Optionally include the whole response
        if node.include_message_in_output:
            data.update(response.model_dump(mode='json'))

        # Extract structured output if JSON schema was used
        if node.use_json_schema or (node.use_json_schema is None and node.json_schema):
            # ALWAYS use a json_schema in production.
            for output in response.output:
                if output.type == 'message':
                    for content in output.content:
                        if content.type == 'output_text':
                            update_data_from_json(data, content.text, node=node)
        else:
            for output in response.output:
                if output.type == 'message':
                    for content in output.content:
                        if content.type == 'output_text':
                            update_data_from_text(data, content.text, node=node)

        return data
