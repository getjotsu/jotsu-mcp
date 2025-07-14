import logging
import time
import typing

import pydantic
from mcp.server.fastmcp import FastMCP
from mcp.types import Resource

from jotsu.mcp.types import Workflow
from jotsu.mcp.local import LocalMCPClient
from jotsu.mcp.client.client import MCPClient
from jotsu.mcp.types.models import WorkflowNode, WorkflowModelUsage, WorkflowData

from .handler import WorkflowHandler, WorkflowHandlerResult
from .sessions import WorkflowSessionManager

logger = logging.getLogger(__name__)


class _WorkflowRef(pydantic.BaseModel):
    id: str
    name: str


class _WorkflowNodeRef(_WorkflowRef):
    type: str

    @classmethod
    def from_node(cls, node: WorkflowNode):
        return cls(id=node.id, name=node.name, type=node.type)


class WorkflowAction(pydantic.BaseModel):
    action: str
    timestamp: float = 0

    @pydantic.model_validator(mode='before')  # noqa
    @classmethod
    def set_defaults(cls, values):
        if values.get('timestamp') is None:
            values['timestamp'] = time.perf_counter()
        return values


class WorkflowActionStart(WorkflowAction):
    action: typing.Literal['workflow-start'] = 'workflow-start'
    workflow: _WorkflowRef
    data: WorkflowData = None


class WorkflowActionEnd(WorkflowAction):
    action: typing.Literal['workflow-end'] = 'workflow-end'
    workflow: _WorkflowRef
    duration: float
    usage: list[WorkflowModelUsage]


class WorkflowActionNodeStart(WorkflowAction):
    action: typing.Literal['node-start'] = 'node-start'
    node: _WorkflowNodeRef
    data: WorkflowData


class WorkflowActionNodeEnd(WorkflowAction):
    action: typing.Literal['node-start'] = 'node-end'
    node: _WorkflowNodeRef
    results: typing.List[WorkflowHandlerResult]


class WorkflowActionDefault(WorkflowAction):
    action: typing.Literal['node-start'] = 'default'
    node: _WorkflowNodeRef
    data: dict


class WorkflowEngine(FastMCP):
    def __init__(
            self, workflows: Workflow | typing.List[Workflow], *args,
            client: typing.Optional[MCPClient] = None, handler_cls: typing.Type[WorkflowHandler] = None,
            **kwargs
    ):
        self._workflows = [workflows] if isinstance(workflows, Workflow) else workflows
        self._client = client if client else LocalMCPClient()
        self._handler = handler_cls(self) if handler_cls is not None else WorkflowHandler(engine=self)

        super().__init__(*args, **kwargs)
        self.add_tool(self.run_workflow, name='workflow')

        for workflow in self._workflows:
            name = workflow.name if workflow.name else workflow.id
            resource = Resource(
                name=name,
                description=workflow.description,
                uri=pydantic.AnyUrl(f'workflow://{workflow.id}/'),
                mimeType='application/json'
            )
            self.add_resource(resource)

    @property
    def anthropic_client(self):
        if not hasattr(self, '_anthropic'):
            from anthropic import AsyncAnthropic
            setattr(self, '_anthropic', AsyncAnthropic())
        return getattr(self, '_anthropic')

    def _get_workflow(self, name: str) -> Workflow | None:
        for workflow in self._workflows:
            if workflow.id == name:
                return workflow
        for workflow in self._workflows:
            if workflow.name == name:
                return workflow
        return None

    @staticmethod
    def _results(
            node: WorkflowNode, values: dict | typing.List[WorkflowHandlerResult]
    ) -> typing.List[WorkflowHandlerResult]:
        return [WorkflowHandlerResult(edge=edge, data=values) for edge in node.edges] \
            if isinstance(values, dict) else values

    async def _run_workflow_node(
            self, workflow: Workflow, node: WorkflowNode, data: dict, *,
            nodes: typing.Dict[str, WorkflowNode], sessions: WorkflowSessionManager, usage: list[WorkflowModelUsage]
    ):
        ref = _WorkflowNodeRef.from_node(node)

        method = getattr(self._handler, f'handle_{node.type}', None)
        if method:
            yield WorkflowActionNodeStart(node=ref, data=data).model_dump()

            result = await method(data, workflow=workflow, node=node, sessions=sessions, usage=usage)
            results: typing.List[WorkflowHandlerResult] = self._results(node, result)

            yield WorkflowActionNodeEnd(node=ref, results=results).model_dump()
        else:
            yield WorkflowActionDefault(node=ref, data=data).model_dump()
            results: typing.List[WorkflowHandlerResult] = self._results(node, data)

        for result in results:
            node = nodes[result.edge]
            async for status in self._run_workflow_node(
                    workflow, node, result.data, nodes=nodes, sessions=sessions, usage=usage
            ):
                yield status

    async def run_workflow(self, name: str, data: dict = None):
        start = time.perf_counter()
        usage: list[WorkflowModelUsage] = []

        workflow = self._get_workflow(name)
        if not workflow:
            logger.error('Workflow not found: %s', name)
            raise ValueError(f'Workflow not found: {name}')

        workflow_name = f'{workflow.name} [{workflow.id}]' if workflow.name != workflow.id else workflow.name
        logger.info("Running workflow '%s'.", workflow_name)

        payload = workflow.data if workflow.data else {}
        if data:
            payload.update(data)

        ref = _WorkflowRef(id=workflow.id, name=workflow.name or workflow.id)
        yield WorkflowActionStart(workflow=ref, timestamp=start, data=payload).model_dump()

        nodes = {node.id: node for node in workflow.nodes}
        node = nodes.get(workflow.start_node_id)

        if not node:
            end = time.perf_counter()
            duration = end - start

            yield WorkflowActionEnd(workflow=ref, timestamp=end, duration=duration, usage=usage).model_dump()

            logger.info(
                "Empty workflow '%s' completed successfully in %s seconds.",
                workflow_name, f'{end - start:.4f}'
            )
            return

        async with WorkflowSessionManager(workflow, client=self._client).context() as sessions:
            for session in sessions.values():  # type: 'MCPClientSession'
                await session.load()

            async for status in self._run_workflow_node(
                    workflow, node, data=payload, nodes=nodes, sessions=sessions, usage=usage
            ):
                yield status

            end = time.perf_counter()
            duration = end - start

            yield WorkflowActionEnd(workflow=ref, timestamp=end, duration=duration, usage=usage).model_dump()
            logger.info("Workflow '%s' completed successfully in %s seconds.", workflow_name, f'{duration:.4f}')
