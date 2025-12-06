import typing
from abc import ABC, abstractmethod

from jotsu.mcp.types.models import WorkflowRulesNode, WorkflowSwitchNode
from jotsu.mcp.workflow.handler.types import WorkflowHandlerResult


class SwitchMixin(ABC):

    @abstractmethod
    async def _handle_rules(self, node: WorkflowRulesNode, data: dict) -> typing.AsyncIterator[WorkflowHandlerResult]:
        yield WorkflowHandlerResult(edge='', data=None)  # pragma: no cover

    async def handle_switch(
            self, data: dict, *, node: WorkflowSwitchNode, **_kwargs
    ) -> typing.AsyncIterator[WorkflowHandlerResult]:
        async for result in self._handle_rules(node, data):
            yield result
