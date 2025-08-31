from jotsu.mcp.types.models import WorkflowPickNode
from jotsu.mcp.workflow import WorkflowEngine


async def test_pick():
    engine = WorkflowEngine([])

    # noinspection PyArgumentList
    node = WorkflowPickNode.model_create(expressions={'foo': 'baz'})
    result = await engine.handler.handle_pick({'baz': 3}, node=node)
    assert result == {'foo': 3}
