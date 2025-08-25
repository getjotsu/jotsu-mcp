import logging
import typing
from abc import ABC, abstractmethod

from jotsu.mcp.types import WorkflowModelUsage, Workflow
from jotsu.mcp.types.models import WorkflowAnthropicNode
from jotsu.mcp.workflow import utils
from .utils import JSON_SCHEMA

if typing.TYPE_CHECKING:
    from jotsu.mcp.workflow import WorkflowEngine  # type: ignore


logger = logging.getLogger(__name__)


class AnthropicMixin(ABC):

    @property
    @abstractmethod
    def engine(self, *args, **kwargs) -> 'WorkflowEngine':
        ...

    async def handle_anthropic(
            self, data: dict, *, action_id: str, workflow: Workflow, node: WorkflowAnthropicNode,
            usage: typing.List[WorkflowModelUsage], **_kwargs
    ):
        from anthropic.types.beta.beta_message import BetaMessage
        from anthropic.types.beta.beta_tool_use_block import BetaToolUseBlock
        from anthropic.types.beta.beta_request_mcp_server_url_definition_param import \
            BetaRequestMCPServerURLDefinitionParam

        client = self.engine.anthropic_client

        messages = data.get('messages', None)
        if messages is None:
            messages = []
            prompt = data.get('prompt', node.prompt)
            if prompt:
                messages.append({'role': 'user', 'content': utils.pybars_render(prompt, data)})

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
        if workflow.servers:
            kwargs['mcp_servers'] = []
            kwargs['betas'] = ['mcp-client-2025-04-04']
            for server in workflow.servers:
                param = BetaRequestMCPServerURLDefinitionParam(name=server.name, type='url', url=str(server.url))
                authorization = server.headers.get('authorization')
                if authorization:
                    param['authorization_token'] = authorization
                kwargs['mcp_servers'].append(param)

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
                    data.update(typing.cast(dict, content.input))  # object type

        return data
