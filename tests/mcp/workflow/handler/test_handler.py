import pytest

from jotsu.mcp.types.exceptions import JotsuException
from jotsu.mcp.types.models import WorkflowMCPNode, WorkflowLoopNode, WorkflowSwitchNode, WorkflowFunctionNode, \
    WorkflowTransformNode, WorkflowTransform
from jotsu.mcp.types.rules import GreaterThanEqualRule, LessThanRule
from jotsu.mcp.workflow import WorkflowEngine
from jotsu.mcp.workflow.handler import WorkflowHandler


async def test_handler_bad_session(mocker):
    engine = WorkflowEngine([])
    node = WorkflowMCPNode(id='1', name='test-tool', type='tool', server_id='test')

    handler = WorkflowHandler(engine=engine)
    sessions = mocker.AsyncMock()
    sessions.get_session.return_value = None

    with pytest.raises(JotsuException):
        await handler.handle_tool({}, sessions=sessions, node=node)


async def test_handler_switch():
    engine = WorkflowEngine([])
    node = WorkflowSwitchNode(
        id='1', name='test-switch', expr='x.y',
        rules=[LessThanRule(value=2), GreaterThanEqualRule(value=2)],
        edges=['e1', 'e2', 'e3']
    )

    handler = WorkflowHandler(engine=engine)

    results = await handler.handle_switch({'x': {'y': 3}}, node=node)

    expected = [
        {'edge': 'e2', 'data': {'x': {'y': 3}}},
        {'edge': 'e3', 'data': {'x': {'y': 3}}},
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_loop():
    engine = WorkflowEngine([])
    node = WorkflowLoopNode(id='1', name='test-loop', expr='lines', edges=['e1', 'e2'])

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_loop({'lines': ['1', '2', '3']}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'lines': ['1', '2', '3'], '__each__': '1'}},
        {'edge': 'e1', 'data': {'lines': ['1', '2', '3'], '__each__': '2'}},
        {'edge': 'e1', 'data': {'lines': ['1', '2', '3'], '__each__': '3'}},
        {'edge': 'e2', 'data': {'lines': ['1', '2', '3'], '__each__': '1'}},
        {'edge': 'e2', 'data': {'lines': ['1', '2', '3'], '__each__': '2'}},
        {'edge': 'e2', 'data': {'lines': ['1', '2', '3'], '__each__': '3'}},
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_loop_rules():
    engine = WorkflowEngine([])
    node = WorkflowLoopNode(
        id='1', name='test-loop', expr='lines',
        rules=[GreaterThanEqualRule(value=2)],
        edges=['e1', 'e2'])

    handler = WorkflowHandler(engine=engine)

    results = await handler.handle_loop({'lines': [1, 2, 3]}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'lines': [1, 2, 3], '__each__': 2}},
        {'edge': 'e1', 'data': {'lines': [1, 2, 3], '__each__': 3}},
        {'edge': 'e2', 'data': {'lines': [1, 2, 3], '__each__': 1}},
        {'edge': 'e2', 'data': {'lines': [1, 2, 3], '__each__': 2}},
        {'edge': 'e2', 'data': {'lines': [1, 2, 3], '__each__': 3}},
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_function():
    engine = WorkflowEngine([])
    node = WorkflowFunctionNode(
        id='1', name='test-function',
        function='return data',
        edges=['e1', 'e2']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_function({'x': {'y': 3}}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'x': {'y': 3}}},
        {'edge': 'e2', 'data': {'x': {'y': 3}}},
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_function_per_edge():
    engine = WorkflowEngine([])
    node = WorkflowFunctionNode(
        id='1', name='test-function',
        function='return [data, None]',
        edges=['e1', 'e2']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_function({'x': {'y': 3}}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'x': {'y': 3}}},
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_function_empty():
    engine = WorkflowEngine([])
    node = WorkflowFunctionNode(
        id='1', name='test-function',
        function='return [data, None]'
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_function({'x': {'y': 3}}, node=node)
    assert [x.model_dump() for x in results] == []


async def test_handler_transform_move():
    engine = WorkflowEngine([])

    transform = WorkflowTransform(type='move', source='a', target='b')

    node = WorkflowTransformNode(
        id='1', name='test-transform',
        transforms=[transform],
        edges=['e1']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_transform({'a': 3}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'b': 3}}
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_transform_set():
    engine = WorkflowEngine([])

    transform = WorkflowTransform(type='set', source='$string(a * 2)', target='b.foo.bar')

    node = WorkflowTransformNode(
        id='1', name='test-transform',
        transforms=[transform],
        edges=['e1']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_transform({'a': 3}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'a': 3, 'b': {'foo': {'bar': '6'}}}}
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_transform_set_constant():
    engine = WorkflowEngine([])

    transform = WorkflowTransform(type='set', source='"c"', target='a.b')

    node = WorkflowTransformNode(
        id='1', name='test-transform',
        transforms=[transform],
        edges=['e1']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_transform({'a': {'b': 3}}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'a': {'b': 'c'}}}
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_transform_delete():
    engine = WorkflowEngine([])

    transform = WorkflowTransform(type='delete', source='a')

    node = WorkflowTransformNode(
        id='1', name='test-transform',
        transforms=[transform],
        edges=['e1']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_transform({'a': 3}, node=node)

    assert [x.model_dump() for x in results] == [{'edge': 'e1', 'data': {}}]
