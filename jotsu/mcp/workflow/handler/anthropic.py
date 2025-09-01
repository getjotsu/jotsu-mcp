import logging
import typing

from jotsu.mcp.types import WorkflowModelUsage, Workflow
from jotsu.mcp.types.models import WorkflowAnthropicNode
from jotsu.mcp.workflow import utils
from .utils import get_messages, update_data_from_text, update_data_from_json

logger = logging.getLogger(__name__)


JSON_SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    'type': 'object',
    'additionalProperties': True
}


class AnthropicMixin:

    @property
    def anthropic_client(self):
        if not hasattr(self, '_anthropic'):
            from anthropic import AsyncAnthropic
            setattr(self, '_anthropic', AsyncAnthropic())
        return getattr(self, '_anthropic')

    async def handle_anthropic(
            self, data: dict, *, action_id: str, workflow: Workflow, node: WorkflowAnthropicNode,
            usage: typing.List[WorkflowModelUsage], **_kwargs
    ):
        from anthropic.types.beta.beta_message import BetaMessage
        from anthropic.types.beta.beta_tool_use_block import BetaToolUseBlock
        from anthropic.types.beta.beta_request_mcp_server_url_definition_param import \
            BetaRequestMCPServerURLDefinitionParam

        client = self.anthropic_client

        messages = get_messages(data, node.prompt)

        kwargs = {}
        system = data.get('system', node.system)
        if system:
            kwargs['system'] = utils.pybars_render(system, data)
        if node.use_json_schema or (node.use_json_schema is None and node.json_schema):
            tool = {
                'name': 'structured_output',
                'input_schema': node.json_schema if node.json_schema else JSON_SCHEMA
            }
            kwargs['tools'] = [tool]
        if node.servers:
            servers = {server.id: server for server in workflow.servers}

            kwargs['mcp_servers'] = []
            kwargs['betas'] = ['mcp-client-2025-04-04']
            for server_id in node.servers:
                server = servers.get(server_id)
                if server:
                    param = BetaRequestMCPServerURLDefinitionParam(name=server.name, type='url', url=str(server.url))
                    authorization = server.headers.get('authorization')
                    if authorization:
                        if authorization.lower().startswith('bearer'):
                            authorization = authorization[6:].strip()
                        param['authorization_token'] = authorization
                    kwargs['mcp_servers'].append(param)
                else:
                    logger.warning('MCP server not found: %s', server_id)

        message: BetaMessage = await client.beta.messages.create(
            max_tokens=node.max_tokens,
            model=node.model,
            messages=messages,
            **kwargs
        )

        usage.append(WorkflowModelUsage(ref_id=action_id, model=node.model, **message.usage.model_dump(mode='json')))

        if node.include_message_in_output:
            data.update(message.model_dump(mode='json'))

        if node.json_schema:
            for content in message.content:
                if content.type == 'tool_use' and content.name == 'structured_output':
                    content = typing.cast(BetaToolUseBlock, content)
                    update_data_from_json(data, content.input, node=node)
        else:
            for content in message.content:
                if content.type == 'text':
                    update_data_from_text(data, content.text, node=node)

        return data
