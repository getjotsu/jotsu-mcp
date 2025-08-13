from jotsu.mcp.workflow.utils import asteval, path_delete, transform_cast


def test_asteval():
    data = {'x': 2}
    expr = 'data["x"] += 2\nreturn data'
    assert asteval(data, expr, node=None) == {'x': 4}


def test_path_delete():
    data = {'a': {'b': 1}}
    path_delete(data, path='a.b')
    assert data == {'a': {}}

    path_delete(data, path='a.b.c')
    assert data == {'a': {}}

    data = {'a': 1}
    path_delete(data, path='a.b.c')
    assert data == {'a': 1}


def test_transform_cast():
    assert transform_cast('a', datatype=None) == 'a'
    assert transform_cast(True, datatype='string') == 'True'
    assert transform_cast('123', datatype='number') == 123
    assert transform_cast('123', datatype='integer') == 123
    assert transform_cast('123.5', datatype='number') == 123.5
    assert transform_cast('a', datatype='boolean') is True
    assert transform_cast(0, datatype='boolean') is False
