import asyncio
import logging
import sys
import time
import typing
import traceback

import pydantic
import jsonschema
from mcp.server.fastmcp import FastMCP
from mcp.types import Resource

from jotsu.mcp.types import Workflow
from jotsu.mcp.local import LocalMCPClient
from jotsu.mcp.client.client import MCPClient
from jotsu.mcp.types.models import WorkflowNode, WorkflowModelUsage, WorkflowData, slug, WorkflowEvent

from .handler import WorkflowHandler, WorkflowHandlerResult
from .handler.utils import is_async_generator, is_result_or_complete_node
from .sessions import WorkflowSessionManager

logger = logging.getLogger(__name__)


class _WorkflowCompleteException(Exception):
    ...


class _WorkflowRef(pydantic.BaseModel):
    id: str
    name: str


class _WorkflowNodeRef(_WorkflowRef):
    type: str

    @classmethod
    def from_node(cls, node: WorkflowNode):
        return cls(id=node.id, name=node.name, type=node.type)


class _WorkflowTracebackFrame(pydantic.BaseModel):
    filename: str
    lineno: int
    func_name: str
    text: str


class WorkflowAction(pydantic.BaseModel):
    action: str
    timestamp: float = 0
    id: typing.Annotated[str, 'The id of this action instance'] = pydantic.Field(default_factory=slug)
    run_id: typing.Annotated[str, 'The id of this run instance']

    @pydantic.model_validator(mode='before')  # noqa
    @classmethod
    def set_defaults(cls, values):
        if values.get('timestamp') is None:
            values['timestamp'] = time.time()
        return values


class WorkflowActionStart(WorkflowAction):
    action: typing.Literal['workflow-start'] = 'workflow-start'
    workflow: _WorkflowRef
    data: WorkflowData = None


class WorkflowActionSchemaError(WorkflowAction):
    action: typing.Literal['schema-error'] = 'workflow-schema-error'
    workflow: _WorkflowRef
    message: str
    exc_type: str
    traceback: typing.List[_WorkflowTracebackFrame]


class WorkflowActionEnd(WorkflowAction):
    action: typing.Literal['workflow-end'] = 'workflow-end'
    workflow: _WorkflowRef
    duration: float
    result: dict | None = None


class WorkflowActionFailed(WorkflowAction):
    action: typing.Literal['workflow-failed'] = 'workflow-failed'
    workflow: _WorkflowRef
    duration: float


class WorkflowActionNodeStart(WorkflowAction):
    action: typing.Literal['node-start'] = 'node-start'
    node: _WorkflowNodeRef
    data: WorkflowData


class WorkflowActionNode(WorkflowAction):
    action: typing.Literal['node-end'] = 'node'
    node: _WorkflowNodeRef
    data: WorkflowData
    duration: float
    start_id: str | None = None
    usage: list[WorkflowModelUsage]


# Keep old name too.
WorkflowActionNodeEnd = WorkflowActionNode


class WorkflowActionNodeError(WorkflowAction):
    action: typing.Literal['node-error'] = 'node-error'
    node: _WorkflowNodeRef
    message: str
    exc_type: str
    traceback: typing.List[_WorkflowTracebackFrame]
    usage: list[WorkflowModelUsage]


class WorkflowActionDefault(WorkflowAction):
    action: typing.Literal['default'] = 'default'
    node: _WorkflowNodeRef
    data: dict


class WorkflowEngine(FastMCP):
    MOCKS = '__mocks__'
    MOCK_TYPE = '__type__'

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
            self._preprocess_workflow(workflow)
            resource = Resource(
                name=workflow.name,
                description=workflow.description,
                uri=pydantic.AnyUrl(f'workflow://{workflow.id}/'),
                mimeType='application/json'
            )
            self.add_resource(resource)

    @property
    def handler(self) -> WorkflowHandler:
        return self._handler

    async def _run_workflow_node(
            self, workflow: Workflow, node: WorkflowNode, data: dict, *,
            nodes: typing.Dict[str, WorkflowNode], sessions: WorkflowSessionManager,
            run_id: str, mocks: typing.Dict[str, dict]
    ):
        ref = _WorkflowNodeRef.from_node(node)

        start_action_id = slug()
        end_action_id = slug()

        handler = getattr(self._handler, f'handle_{node.type}', None)
        if handler:
            start = time.time()
            yield WorkflowActionNodeStart(
                id=start_action_id, node=ref, data=data, run_id=run_id, timestamp=start
            ).model_dump()

            usage: typing.List[WorkflowModelUsage] = []
            try:
                complete_exception = None
                try:
                    async for handler_result in self._iterate_handler(
                            node, handler, data,
                            mocks=mocks, action_id=end_action_id, workflow=workflow, sessions=sessions, usage=usage,
                    ):
                        next_node = nodes[handler_result.edge]
                        async for child_result in self._run_workflow_node(
                                workflow, next_node, handler_result.data, nodes=nodes,
                                sessions=sessions, run_id=run_id, mocks=mocks
                        ):
                            yield child_result
                            data = child_result['data'] if 'data' in child_result else data

                except _WorkflowCompleteException as e:
                    # Ensures the end node is output.
                    complete_exception = e

                end = time.time()
                yield WorkflowActionNode(
                    id=end_action_id, node=ref, data=data, run_id=run_id,
                    timestamp=end, duration=end - start, start_id=start_action_id,
                    usage=usage
                ).model_dump()
                # FIXME: add usage here!

                if complete_exception:
                    raise complete_exception

                end_node_id = getattr(node, 'end_node_id', None)
                if end_node_id:
                    async for child_result in self._run_workflow_node(
                            workflow, nodes[end_node_id], data, nodes=nodes,
                            sessions=sessions, run_id=run_id, mocks=mocks
                    ):
                        yield child_result
                        data = child_result['data'] if 'data' in child_result else data

            except _WorkflowCompleteException as e:
                raise e
            except Exception as e:  # noqa
                logger.exception('handler exception')

                # If there is only one exception in the group, return that instead.
                if isinstance(e, ExceptionGroup):
                    if len(e.exceptions) == 1:
                        e = e.exceptions[0]

                exc_type = type(e)
                tb = e.__traceback__

                yield WorkflowActionNodeError(
                    node=ref, message=str(e), run_id=run_id, usage=usage,
                    exc_type=exc_type.__name__, traceback=list(self._get_tb(tb))
                ).model_dump()

                raise e
        else:
            # result and complete don't have handlers.
            yield WorkflowActionNode(
                id=end_action_id, node=ref, data=data, run_id=run_id,
                timestamp=time.time(), duration=0, usage=[]
            ).model_dump()

            if node.type == 'complete':
                raise _WorkflowCompleteException(data)

            for node_id in node.edges:
                next_node = nodes[node_id]
                async for child_data in self._run_workflow_node(
                        workflow, next_node, data, nodes=nodes,
                        sessions=sessions, run_id=run_id, mocks=mocks
                ):
                    yield child_data

    async def get_workflow(self, name: str):
        return self._get_workflow(name)

    async def run_workflow(self, name: str, data: dict = None, *, run_id: str = None):
        start = time.time()
        workflow_result_data: dict | None = None

        workflow = await self._workflow(name)

        run_id = run_id if run_id else slug()
        workflow_name = f'{workflow.name} [{workflow.id}]' if workflow.name != workflow.id else workflow.name
        logger.info("Running workflow '%s'.", workflow_name)

        payload = workflow.data.copy() if workflow.data else {}
        if data:
            payload.update(data)

        mocks = payload.pop(self.MOCKS, {})

        ref = _WorkflowRef(id=workflow.id, name=workflow.name or workflow.id)
        yield WorkflowActionStart(workflow=ref, timestamp=start, data=payload, run_id=run_id).model_dump()

        if workflow.event and workflow.event.json_schema:
            try:
                jsonschema.validate(instance=payload, schema=workflow.event.json_schema)
            except jsonschema.ValidationError as e:
                exc_type, _, tb = sys.exc_info()
                yield WorkflowActionSchemaError(
                    workflow=ref, message=str(e), run_id=run_id,
                    exc_type=exc_type.__name__, traceback=list(self._get_tb(tb)),
                ).model_dump()

                end = time.time()
                duration = end - start
                yield WorkflowActionFailed(
                    workflow=ref, timestamp=end, duration=duration, run_id=run_id
                ).model_dump()
                logger.info(
                    "Workflow '%s' failed due to invalid schema in %s seconds.",
                    workflow_name, f'{duration:.4f}'
                )
                return

        nodes = {node.id: node for node in workflow.nodes}

        start_node_id = workflow.start_node_id
        if not start_node_id:
            start_node_id = workflow.nodes[0].id if len(workflow.nodes) else None
        node = nodes.get(start_node_id) if start_node_id else None

        if not node:
            end = time.time()
            duration = end - start

            yield WorkflowActionEnd(workflow=ref, timestamp=end, duration=duration, run_id=run_id).model_dump()
            logger.info(
                "Empty workflow '%s' completed successfully in %s seconds.",
                workflow_name, f'{end - start:.4f}'
            )
            return

        sessions = WorkflowSessionManager(workflow, client=self._client)
        try:
            success = True
            try:
                async for result in self._run_workflow_node(
                        workflow, node, data=payload, nodes=nodes,
                        sessions=sessions, run_id=run_id, mocks=mocks,
                ):
                    # check for result
                    yield result
                    if is_result_or_complete_node(result):
                        workflow_result_data = result.get('data')
            except _WorkflowCompleteException:
                # This works since the yield happens before the exception.
                pass
            except:  # noqa
                success = False

            end = time.time()
            duration = end - start

            if success:
                yield WorkflowActionEnd(
                    result=workflow_result_data, workflow=ref,
                    timestamp=end, duration=duration, run_id=run_id
                ).model_dump()
                logger.info(
                    "Workflow '%s' completed successfully in %s seconds.",
                    workflow_name, f'{duration:.4f}'
                )
            else:
                yield WorkflowActionFailed(workflow=ref, timestamp=end, duration=duration, run_id=run_id).model_dump()
                logger.info(
                    "Workflow '%s' failed in %s seconds.",
                    workflow_name, f'{duration:.4f}'
                )
        finally:
            try:
                if not self.is_shutting_down() or sessions.is_owner():
                    await sessions.aclose()
            except asyncio.CancelledError:
                # Also normal during shutdown; don't log as an error
                pass
            except:  # noqa
                # Downgrade to warning or debug if this only happens on shutdown
                logger.warning('Error while closing MCPClient session', exc_info=True)

    # noinspection PyMethodMayBeStatic
    def is_shutting_down(self):
        """This function can be overridden to test for process exit and avoid noisy cleanup warnings."""
        return False

    @staticmethod
    def _preprocess_workflow(workflow: Workflow):
        workflow.name = workflow.name or workflow.id
        workflow.event = workflow.event or WorkflowEvent()

        for node in workflow.nodes:
            node.name = node.name or node.id

    # Helper for get_workflow()
    def _get_workflow(self, name: str) -> Workflow | None:
        for workflow in self._workflows:
            if workflow.id == name:
                return workflow
        for workflow in self._workflows:
            if workflow.name == name:
                return workflow
        return None

    async def _workflow(self, name: str) -> Workflow:
        workflow = await self.get_workflow(name)
        if not workflow:
            logger.error('Workflow not found: %s', name)
            raise ValueError(f'Workflow not found: {name}')
        return workflow

    @staticmethod
    def _get_tb(tb):
        for frame in traceback.extract_tb(tb, 64):
            yield _WorkflowTracebackFrame(
                filename=frame.filename, lineno=frame.lineno, func_name=frame.name, text=frame.line
            )

    async def _iterate_handler(
            self, node: WorkflowNode, method, data, *,
            mocks: typing.Dict[str, dict], usage: typing.List[WorkflowModelUsage],
            **kwargs
    ) -> typing.AsyncIterator[WorkflowHandlerResult]:
        # A handler returns either a simple dict or an async iterator of WorkflowHandlerResults.
        # Any model usage is stored in the usages list.
        if node.id not in mocks:
            if is_async_generator(method):
                # Test for a generator which returns an iterator...
                async for result in method(data, node=node, **kwargs):
                    yield result
            else:
                for node_id in node.edges:
                    data = await method(data, node=node, usage=usage, **kwargs)
                    yield WorkflowHandlerResult(edge=node_id, data=data)
        else:
            mock = mocks[node.id].copy()

            if isinstance(mock, list):
                for item in mock:
                    # All list mocks are 'replace'.
                    yield WorkflowHandlerResult(**item)
            else:
                mock_type = mock.pop(self.MOCK_TYPE, '')
                if mock_type.lower() == 'replace':
                    result = mock
                else:
                    result = data | mock

                for node_id in node.edges:
                    yield WorkflowHandlerResult(edge=node_id, data=result)
