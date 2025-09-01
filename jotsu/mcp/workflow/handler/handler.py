import json
import logging
import typing

import pydantic
from mcp.types import ReadResourceResult, GetPromptResult

from jotsu.mcp.types.rules import Rule
from jotsu.mcp.types.models import (
    WorkflowMCPNode,
    WorkflowSwitchNode, WorkflowLoopNode,
    WorkflowRulesNode
)
from jotsu.mcp.client.client import MCPClientSession

from jotsu.mcp.workflow.sessions import WorkflowSessionManager

from .types import WorkflowHandlerResult
from .utils import jsonata_value, get_server_from_session_manager

from .anthropic import AnthropicMixin
from .cloudflare import CloudflareMixin
from .openai import OpenAIMixin
from .function import FunctionMixin
from .pick import PickMixin
from .tools import ToolMixin
from .transform import TransformMixin

if typing.TYPE_CHECKING:
    from jotsu.mcp.workflow.engine import WorkflowEngine  # type: ignore

logger = logging.getLogger(__name__)


class WorkflowHandler(
    AnthropicMixin, OpenAIMixin, CloudflareMixin,
    ToolMixin,
    FunctionMixin, PickMixin, TransformMixin
):
    def __init__(self, engine: 'WorkflowEngine'):
        self._engine = engine

    async def handle_resource(
            self, data: dict, *,
            node: WorkflowMCPNode, sessions: WorkflowSessionManager, **_kwargs
    ):
        session = await self._get_session(node.server_id, sessions=sessions)

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
        session = await self._get_session(node.server_id, sessions=sessions)

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

    def _handle_rules(self, node: WorkflowRulesNode, data: dict):
        results = []
        value = jsonata_value(data, node.expr) if node.expr else data
        for i, edge in enumerate(node.edges):
            rule = self._get_rule(node.rules, i)
            if rule:
                if rule.test(value):
                    results.append(WorkflowHandlerResult(edge=edge, data=data))
            else:
                results.append(WorkflowHandlerResult(edge=edge, data=data))

        return results

    async def handle_switch(
            self, data: dict, *, node: WorkflowSwitchNode, **_kwargs
    ) -> typing.List[WorkflowHandlerResult]:
        return self._handle_rules(node, data)

    async def handle_loop(
            self, data: dict, *, node: WorkflowLoopNode, **_kwargs
    ) -> typing.List[WorkflowHandlerResult]:
        results = []

        values = jsonata_value(data, node.expr)
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

    @staticmethod
    def _get_rule(rules: typing.List[Rule] | None, index: int) -> Rule | None:
        if rules and len(rules) > index:
            return rules[index]
        return None

    async def _get_session(self, server_id: str, *, sessions: WorkflowSessionManager) -> MCPClientSession:
        server = get_server_from_session_manager(server_id=server_id, sessions=sessions)
        return await sessions.get_session(server)

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
