import typing
from abc import ABC, abstractmethod

from jotsu.mcp.types import WorkflowLoopNode, Rule
from jotsu.mcp.workflow.handler.types import WorkflowHandlerResult
from jotsu.mcp.workflow.handler.utils import jsonata_value


class LoopMixin(ABC):

    @staticmethod
    @abstractmethod
    def _get_rule(rules: typing.List[Rule] | None, index: int):
        ...

    async def handle_loop(
            self, data: dict, *, node: WorkflowLoopNode, **_kwargs
    ) -> typing.AsyncIterator[WorkflowHandlerResult]:

        for i, edge in enumerate(node.edges):
            rule = self._get_rule(node.rules, i)

            values = jsonata_value(data, node.expr)
            for value in values:
                result = None

                data[node.member or '__each__'] = value
                if rule:
                    if rule.test(value):
                        result = WorkflowHandlerResult(edge=edge, data=data)
                else:
                    result = WorkflowHandlerResult(edge=edge, data=data)

                if result:
                    data = result.data
                    yield result
