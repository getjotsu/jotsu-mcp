import logging
from abc import ABC, abstractmethod

import jsonschema
from mcp.types import CallToolResult, Tool

from jotsu.mcp.client.client import MCPClientSession
from jotsu.mcp.types import WorkflowMCPNode, JotsuException
from jotsu.mcp.workflow.sessions import WorkflowSessionManager

logger = logging.getLogger(__name__)


class ToolMixin(ABC):
    @abstractmethod
    async def _get_session(self, *args, **kwargs) -> MCPClientSession:
        ...

    @abstractmethod
    def _update_text(self, *args, **kwargs) -> MCPClientSession:
        ...

    @staticmethod
    async def get_tool(session: MCPClientSession, name: str) -> Tool | None:
        res = await session.list_tools()
        for tool in res.tools:
            if tool.name == name:
                return tool
        return None

    async def handle_tool(
            self, data: dict, *,
            node: WorkflowMCPNode, sessions: WorkflowSessionManager, **_kwargs
    ):
        session = await self._get_session(node.server_id, sessions=sessions)

        tool = await self.get_tool(session, node.name)
        if not tool:
            raise JotsuException(f'MCP Tool not found: {node.name}')

        try:
            jsonschema.validate(instance=data, schema=tool.inputSchema)
        except jsonschema.ValidationError as e:
            raise JotsuException(e)

        # tools likely only use the top-level properties
        arguments = {}
        for prop in tool.inputSchema.get('properties', []):
            if prop in data:
                arguments[prop] = data[prop]

        result: CallToolResult = await session.call_tool(node.name, arguments=arguments)
        if result.isError:
            raise JotsuException(f"Error calling tool '{node.name}': {result.content[0].text}.")

        if result.structuredContent:
            if node.member:
                data[node.member] = result.structuredContent
            else:
                data.update(result.structuredContent)
        else:
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
