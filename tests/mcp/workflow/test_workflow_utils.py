from jotsu.mcp.workflow.utils import asteval


def test_asteval():
    data = {'x': 2}
    expr = 'data["x"] += 2\nreturn data'
    assert asteval(data, expr, node=None) == {'x': 4}
