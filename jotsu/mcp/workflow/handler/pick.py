from jotsu.mcp.types.models import WorkflowPickNode
from . import utils


class PickMixin:

    @staticmethod
    async def handle_pick(data: dict, *, node: WorkflowPickNode, **_kwargs):
        result = {}
        for key, expr in node.expressions.items():
            value = utils.jsonata_value(data, expr)
            result[key] = value
        return result
