import logging
from abc import ABC, abstractmethod

from mcp.types import GetPromptResult

from jotsu.mcp.client.client import MCPClientSession
from jotsu.mcp.types import WorkflowMCPNode
from jotsu.mcp.workflow.sessions import WorkflowSessionManager

logger = logging.getLogger(__name__)


class PromptMixin(ABC):
    @abstractmethod
    async def _get_session(self, *args, **kwargs) -> MCPClientSession:
        ...

    @abstractmethod
    def _update_text(self, *args, **kwargs) -> dict:
        ...

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
