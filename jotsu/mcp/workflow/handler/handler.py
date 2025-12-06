import logging
import typing

from jotsu.mcp.types.rules import Rule
from jotsu.mcp.types.models import WorkflowRulesNode
from jotsu.mcp.client.client import MCPClientSession

from jotsu.mcp.workflow.sessions import WorkflowSessionManager
from .loop import LoopMixin
from .switch import SwitchMixin

from .types import WorkflowHandlerResult
from .utils import jsonata_value

from .anthropic import AnthropicMixin
from .cloudflare import CloudflareMixin
from .openai import OpenAIMixin
from .function import FunctionMixin
from .pick import PickMixin
from .prompts import PromptMixin
from .resources import ResourceMixin
from .tools import ToolMixin
from .transform import TransformMixin
from ...types import JotsuException, WorkflowMCPNode

if typing.TYPE_CHECKING:
    from jotsu.mcp.workflow.engine import WorkflowEngine  # type: ignore

logger = logging.getLogger(__name__)


class WorkflowHandler(
    AnthropicMixin, OpenAIMixin, CloudflareMixin,
    ToolMixin, ResourceMixin, PromptMixin,
    FunctionMixin, PickMixin, TransformMixin,
    LoopMixin, SwitchMixin
):
    def __init__(self, engine: 'WorkflowEngine'):
        self._engine = engine

    async def _handle_rules(self, node: WorkflowRulesNode, data: dict) -> typing.AsyncIterator[WorkflowHandlerResult]:
        value = jsonata_value(data, node.expr) if node.expr else data
        for i, edge in enumerate(node.edges):
            rule = self._get_rule(node.rules, i)
            if rule:
                if rule.test(value):
                    yield WorkflowHandlerResult(edge=edge, data=data)
            else:
                yield WorkflowHandlerResult(edge=edge, data=data)

    @staticmethod
    def _get_rule(rules: typing.List[Rule] | None, index: int):
        if rules and len(rules) > index:
            return rules[index]
        return None

    async def _get_session(self, node: WorkflowMCPNode, *, sessions: WorkflowSessionManager) -> MCPClientSession:
        # session_id is either the id of a server or a node.
        session_id = node.server_id if node.server_id else node.id
        session = await sessions.get_session(session_id)
        if not session:
            raise JotsuException(f'Session not found: {session_id}')
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
