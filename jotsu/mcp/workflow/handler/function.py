from jotsu.mcp.types.models import WorkflowFunctionNode
from jotsu.mcp.workflow import utils
from .types import WorkflowHandlerResult


class FunctionMixin:

    # FIXME: add a time limit.
    @staticmethod
    async def handle_function(
            data: dict, *, node: WorkflowFunctionNode, **_kwargs
    ):
        if node.edges:
            result = utils.asteval(data, expr=node.function, node=node)
            match result:
                case _ if isinstance(result, dict):
                    return [WorkflowHandlerResult(edge=edge, data=result) for edge in node.edges]
                case _ if isinstance(result, list):
                    results = []
                    for i, edge in enumerate(node.edges):
                        if i < len(result) and result[i] is not None:
                            results.append(WorkflowHandlerResult(edge=edge, data=result[i]))
                    return results
        return []
