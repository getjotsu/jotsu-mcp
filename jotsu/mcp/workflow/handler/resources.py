import json
import logging
from abc import ABC, abstractmethod

from mcp.types import ReadResourceResult

from jotsu.mcp.client.client import MCPClientSession
from jotsu.mcp.types import WorkflowMCPNode
from jotsu.mcp.workflow.sessions import WorkflowSessionManager

logger = logging.getLogger(__name__)


class ResourceMixin(ABC):
    @abstractmethod
    async def _get_session(self, *args, **kwargs) -> MCPClientSession:
        ...

    @abstractmethod
    def _update_text(self, *args, **kwargs) -> dict:
        ...

    @abstractmethod
    def _update_json(self, *args, **kwargs) -> dict:
        ...

    async def handle_resource(
            self, data: dict, *,
            node: WorkflowMCPNode, sessions: WorkflowSessionManager, **_kwargs
    ):
        session = await self._get_session(node.server_id, sessions=sessions)
        uri = str(node.uri)

        result: ReadResourceResult = await session.read_resource(node.uri)
        for contents in result.contents:
            mime_type = contents.mimeType or ''
            match mime_type:
                case 'application/json':
                    resource = json.loads(contents.text)
                    data = self._update_json(data, update=resource, member=node.member)
                case _ if mime_type.startswith('text/') or getattr(contents, 'text', None):
                    data = self._update_text(data, text=contents.text, member=node.member or uri)
                case _:
                    logger.warning(
                        "Unknown or missing mimeType '%s' for resource '%s'.", mime_type, uri
                    )
        return data
