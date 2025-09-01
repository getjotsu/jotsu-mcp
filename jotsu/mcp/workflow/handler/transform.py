import typing
from abc import ABC, abstractmethod

from jotsu.mcp.types.models import WorkflowTransformNode, WorkflowTransform, WorkflowRulesNode
from jotsu.mcp.workflow.handler.types import WorkflowHandlerResult

from jotsu.mcp.workflow import utils
from .utils import jsonata_value


class TransformMixin(ABC):

    @abstractmethod
    def _handle_rules(self, node: WorkflowRulesNode, data: dict):
        ...

    async def handle_transform(
            self, data: dict, *, node: WorkflowTransformNode, **_kwargs
    ) -> typing.List[WorkflowHandlerResult]:
        for transform in node.transforms:
            transform = WorkflowTransform(**transform) if isinstance(transform, dict) else transform
            source_value = utils.transform_cast(
                jsonata_value(data, transform.source), datatype=transform.datatype
            )

            match transform.type:
                case 'set':
                    utils.path_set(data, path=transform.target, value=source_value)
                case 'move':
                    utils.path_set(data, path=transform.target, value=source_value)
                    utils.path_delete(data, path=transform.source)
                case 'delete':
                    utils.path_delete(data, path=transform.source)

        return self._handle_rules(node, data)
