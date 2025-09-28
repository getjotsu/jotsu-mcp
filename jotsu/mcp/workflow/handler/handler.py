import logging
import typing


from jotsu.mcp.types.rules import Rule
from jotsu.mcp.types.models import (WorkflowSwitchNode, WorkflowLoopNode, WorkflowRulesNode)
from jotsu.mcp.client.client import MCPClientSession

from jotsu.mcp.workflow.sessions import WorkflowSessionManager

from .types import WorkflowHandlerResult
from .utils import jsonata_value, get_server_from_session_manager

from .anthropic import AnthropicMixin
from .cloudflare import CloudflareMixin
from .openai import OpenAIMixin
from .function import FunctionMixin
from .pick import PickMixin
from .prompts import PromptMixin
from .resources import ResourceMixin
from .tools import ToolMixin
from .transform import TransformMixin

if typing.TYPE_CHECKING:
    from jotsu.mcp.workflow.engine import WorkflowEngine  # type: ignore

logger = logging.getLogger(__name__)


class WorkflowHandler(
    AnthropicMixin, OpenAIMixin, CloudflareMixin,
    ToolMixin, ResourceMixin, PromptMixin,
    FunctionMixin, PickMixin, TransformMixin
):
    def __init__(self, engine: 'WorkflowEngine'):
        self._engine = engine

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
