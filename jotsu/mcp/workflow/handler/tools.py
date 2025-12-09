import copy
import json
import logging
import typing
from abc import ABC, abstractmethod

import jsonschema
from mcp.types import CallToolResult, Tool

from jotsu.mcp.client.client import MCPClientSession
from jotsu.mcp.types import JotsuException, WorkflowToolNode
from jotsu.mcp.workflow.handler.types import WorkflowHandlerResult
from jotsu.mcp.workflow.sessions import WorkflowSessionManager

logger = logging.getLogger(__name__)


class ToolMixin(ABC):
    @abstractmethod
    async def _get_session(self, *args, **kwargs) -> MCPClientSession:
        ...

    @abstractmethod
    def _update_text(self, *args, **kwargs) -> dict:
        ...

    @abstractmethod
    def _update_json(self, *args, **kwargs) -> dict:
        ...

    @staticmethod
    async def get_tool(session: MCPClientSession, name: str) -> Tool | None:
        res = await session.list_tools()
        for tool in res.tools:
            if tool.name == name:
                return tool
        return None

    async def _handle_tool(
            self, data: dict, *,
            node: WorkflowToolNode, sessions: WorkflowSessionManager, **_kwargs
    ):
        session = await self._get_session(node, sessions=sessions)
        tool_name = node.tool_name if node.tool_name else node.name

        tool = await self.get_tool(session, tool_name)
        if not tool:
            raise JotsuException(f'MCP Tool not found: {tool_name}')

        self._validate_schema(tool, data)

        # tools likely only use the top-level properties
        arguments = {}
        for prop in tool.inputSchema.get('properties', []):
            if prop in data:
                arguments[prop] = data[prop]
            elif prop == 'kwargs':
                arguments['kwargs'] = data

        result: CallToolResult = await session.call_tool(tool_name, arguments=arguments)
        if result.isError:
            raise JotsuException(f"Error calling tool '{tool_name}': {result.content[0].text}.")

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
                    if node.structured_output:
                        # Tools that yield return lists.
                        result_data = json.loads(content.text)
                        result_data = result_data if isinstance(result_data, list) else [result_data]
                        for update in result_data:
                            data = self._update_json(data, update=update, member=node.member)
                    else:
                        data = self._update_text(data, text=content.text, member=node.member or tool_name)
                else:
                    logger.warning(
                        "Invalid message type '%s' for tool '%s'.", message_type, tool_name
                    )
        return data

    async def handle_tool(
            self, data: dict, *,
            node: WorkflowToolNode, sessions: WorkflowSessionManager, **_kwargs
    ) -> typing.AsyncIterator[WorkflowHandlerResult]:
        if node.edges:
            for edge in node.edges:
                data = await self._handle_tool(data=data, node=node, sessions=sessions, **_kwargs)
                yield WorkflowHandlerResult(edge=edge, data=data)
        else:
            # Tools are the only node with side effects so make sure they are called once even
            # if node edges are defined.
            await self._handle_tool(data=data, node=node, sessions=sessions, **_kwargs)

    # kwargs is a convention meaning 'all data' - so we have to exclude it.
    @staticmethod
    def _validate_schema(tool: Tool, data: dict):
        input_schema = copy.deepcopy(tool.inputSchema)

        properties = input_schema.get('properties', {})
        properties.pop('kwargs', None)
        input_schema['properties'] = properties

        required = input_schema.get('required', [])
        input_schema['required'] = [r for r in required if r != 'kwargs']

        input_schema['additionalProperties'] = True

        try:
            jsonschema.validate(instance=data, schema=input_schema)
        except jsonschema.ValidationError as e:
            raise JotsuException(e)
