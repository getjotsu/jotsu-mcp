import json
import logging
import typing

import jsonata
import pydantic
from mcp.types import ReadResourceResult, GetPromptResult, CallToolResult

from jotsu.mcp.types.exceptions import JotsuException
from jotsu.mcp.types.rules import Rule
from jotsu.mcp.types.models import (
    WorkflowMCPNode,
    WorkflowSwitchNode, WorkflowLoopNode, WorkflowFunctionNode,
    WorkflowAnthropicNode, WorkflowModelUsage, Workflow
)
from jotsu.mcp.client.client import MCPClientSession

from .sessions import WorkflowSessionManager
from .utils import asteval, pybars_render

if typing.TYPE_CHECKING:
    from .engine import WorkflowEngine

logger = logging.getLogger(__name__)


class WorkflowHandlerResult(pydantic.BaseModel):
    edge: str
    data: dict


class WorkflowHandler:
    def __init__(self, engine: 'WorkflowEngine'):
        self._engine = engine

    async def handle_anthropic(
            self, data: dict, *, workflow: Workflow, node: WorkflowAnthropicNode,
            usage: typing.List[WorkflowModelUsage], **_kwargs
    ):
        from anthropic.types.beta.beta_message import BetaMessage
        from anthropic.types.beta.beta_tool_use_block import BetaToolUseBlock
        from anthropic.types.beta.beta_request_mcp_server_url_definition_param import \
            BetaRequestMCPServerURLDefinitionParam

        client = self._engine.anthropic_client

        messages = data.get('messages', None)
        if messages is None:
            messages = []
            prompt = data.get('prompt', node.prompt)
            if prompt:
                messages.append({'role': 'user', 'content': pybars_render(prompt, data)})

        kwargs = {}
        system = data.get('system', node.system)
        if system:
            kwargs['system'] = pybars_render(system, data)
        if node.json_schema:
            kwargs['tools'] = [{'name': 'structured_output', 'input_schema': node.json_schema}]
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

        usage.append(WorkflowModelUsage(node_id=node.id, model=node.model, **message.usage.model_dump(mode='json')))

        if node.include_message_in_output:
            data.update(message.model_dump(mode='json'))

        if node.json_schema:
            for content in message.content:
                if content.type == 'tool_use' and content.name == 'structured_output':
                    content = typing.cast(BetaToolUseBlock, content)
                    data.update(typing.cast(dict, content.input))  # object type

        return data

    async def handle_resource(
            self, data: dict, *,
            node: WorkflowMCPNode, sessions: WorkflowSessionManager, **_kwargs
    ):
        session = self._get_session(node.server_id, sessions=sessions)

        result: ReadResourceResult = await session.read_resource(pydantic.AnyUrl(node.name))
        for contents in result.contents:
            mime_type = contents.mimeType or ''
            match mime_type:
                case 'application/json':
                    resource = json.loads(contents.text)
                    data = self._update_json(data, update=resource, member=node.member)
                case _ if mime_type.startswith('text/') or getattr(contents, 'text', None):
                    data = self._update_text(data, text=contents.text, member=node.member or node.name)
                case _:
                    logger.warning(
                        "Unknown or missing mimeType '%s' for resource '%s'.", mime_type, node.name
                    )
        return data

    async def handle_prompt(
            self, data: dict, *,
            node: WorkflowMCPNode, sessions: WorkflowSessionManager, **_kwargs
    ):
        session = self._get_session(node.server_id, sessions=sessions)

        result: GetPromptResult = await session.get_prompt(node.name, arguments=data)
        for message in result.messages:
            message_type = message.content.type
            if message_type == 'text':
                data = self._update_text(data, text=message.content.text, member=node.member or node.name)
            else:
                logger.warning(
                    "Invalid message type '%s' for prompt '%s'.", message_type, node.name
                )
        return data

    async def handle_tool(
            self, data: dict, *,
            node: WorkflowMCPNode, sessions: WorkflowSessionManager, **_kwargs
    ):
        session = self._get_session(node.server_id, sessions=sessions)

        result: CallToolResult = await session.call_tool(node.name, arguments=data)
        if result.isError:
            raise JotsuException(f"Error calling tool '{node.name}': {result.content[0].text}.")

        for content in result.content:
            message_type = content.type
            if message_type == 'text':
                # Tools don't have a mime type and only text is currently supported.
                data = self._update_text(data, text=content.text, member=node.member or node.name)
            else:
                logger.warning(
                    "Invalid message type '%s' for tool '%s'.", message_type, node.name
                )
        return data

    async def handle_switch(
            self, data: dict, *, node: WorkflowSwitchNode, **_kwargs
    ) -> typing.List[WorkflowHandlerResult]:
        results = []
        value = self._jsonata_value(data, node.expr) if node.expr else data
        for i, edge in enumerate(node.edges):
            rule = self._get_rule(node.rules, i)
            if rule:
                if rule.test(value):
                    results.append(WorkflowHandlerResult(edge=edge, data=data))
            else:
                results.append(WorkflowHandlerResult(edge=edge, data=data))

        return results

    async def handle_loop(
            self, data: dict, *, node: WorkflowLoopNode, **_kwargs
    ) -> typing.List[WorkflowHandlerResult]:
        results = []

        values = self._jsonata_value(data, node.expr)
        for i, edge in enumerate(node.edges):
            rule = self._get_rule(node.rules, i)

            for value in values:
                data[node.member or '__each__'] = value
                if rule:
                    if rule.test(value):
                        results.append(WorkflowHandlerResult(edge=edge, data=data))
                else:
                    results.append(WorkflowHandlerResult(edge=edge, data=data))

        return results

    # FIXME: add a time limit.
    @staticmethod
    async def handle_function(
            data: dict, *, node: WorkflowFunctionNode, **_kwargs
    ):
        if node.edges:
            result = asteval(data, expr=node.function, node=node)
            match result:
                case _ if isinstance(result, dict):
                    return [WorkflowHandlerResult(edge=edge, data=result) for edge in node.edges]
                case _ if isinstance(result, list):
                    results = []
                    for i, edge in enumerate(node.edges):
                        if i < len(result) and result[i] is not None:
                            results.append(WorkflowHandlerResult(edge=edge, data=result[i]))
                    return results
        return []

    @staticmethod
    def _jsonata_value(data: dict, expr: str):
        expr = jsonata.Jsonata(expr)
        return expr.evaluate(data)

    @staticmethod
    def _get_rule(rules: typing.List[Rule] | None, index: int) -> Rule | None:
        if rules and len(rules) > index:
            return rules[index]
        return None

    @staticmethod
    def _get_session(server_id: str, *, sessions: WorkflowSessionManager) -> MCPClientSession:
        session = sessions.get(server_id)
        if not session:
            raise JotsuException('Server not found: %s', server_id)
        return session

    @staticmethod
    def _update_json(data: dict, *, update: dict, member: str | None):
        if member:
            data[member] = update
        else:
            data.update(update)
        return data

    @staticmethod
    def _update_text(data: dict, *, text: str, member: str | None):
        data[member] = text
        return data
