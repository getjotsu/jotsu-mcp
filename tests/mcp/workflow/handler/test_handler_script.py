from jotsu.mcp.types.models import WorkflowScriptNode
from jotsu.mcp.workflow import WorkflowEngine
from jotsu.mcp.workflow.handler import WorkflowHandler


async def test_handler_script():
    engine = WorkflowEngine([])
    node = WorkflowScriptNode(
        id='1', name='test-script',
        script='data.x.y += 1; return data;',
        edges=['e1', 'e2']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_script({'x': {'y': 3}}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'x': {'y': 4}}},
        {'edge': 'e2', 'data': {'x': {'y': 4}}},
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_script_empty():
    engine = WorkflowEngine([])
    node = WorkflowScriptNode(
        id='1', name='test-script',
        script='',
        edges=['e1', 'e2']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_script({'x': {'y': 3}}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'x': {'y': 3}}},
        {'edge': 'e2', 'data': {'x': {'y': 3}}},
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_script_in_place():
    engine = WorkflowEngine([])
    node = WorkflowScriptNode(
        id='1', name='test-script',
        script='data.x.y += 1;',
        edges=['e1', 'e2']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_script({'x': {'y': 3}}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'x': {'y': 4}}},
        {'edge': 'e2', 'data': {'x': {'y': 4}}},
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_script_list():
    engine = WorkflowEngine([])
    node = WorkflowScriptNode(
        id='1', name='test-script',
        script='return [{x: 1}, {y: 2}];',
        edges=['e1', 'e2']
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_script({}, node=node)

    expected = [
        {'edge': 'e1', 'data': {'x': 1}},
        {'edge': 'e2', 'data': {'y': 2}},
    ]

    assert [x.model_dump() for x in results] == expected


async def test_handler_script_no_edges():
    engine = WorkflowEngine([])
    node = WorkflowScriptNode(
        id='1', name='test-script',
        script='data.x.y += 1; return data;',
        edges=[]
    )

    handler = WorkflowHandler(engine=engine)
    results = await handler.handle_script({'x': {'y': 3}}, node=node)

    assert [x.model_dump() for x in results] == []
