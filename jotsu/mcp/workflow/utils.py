import typing

from asteval import Interpreter

from jotsu.mcp.types import JotsuException


def wrap_function(expr: str):
    lines = ['def __func():']
    for line in expr.splitlines():
        lines.append('    ' + line)
    lines.append('')
    lines.append('__func()')
    return '\n'.join(lines)


def asteval(data: dict, expr: str, *, node):
    aeval = Interpreter()
    aeval.symtable['data'] = data
    aeval.symtable['node'] = node
    aeval.symtable.pop('print', None)
    result = aeval(wrap_function(expr))
    if aeval.error:
        raise JotsuException('\n'.join([e.msg for e in aeval.error]))
    return result


def pybars_compiler():  # pragma: no coverage
    if not hasattr(pybars_compiler, '_compiler'):
        from pybars import Compiler
        setattr(pybars_compiler, '_compiler', Compiler())
    return getattr(pybars_compiler, '_compiler')


def pybars_render(source: str, data: any) -> str:
    compiler = pybars_compiler()
    template = compiler.compile(source)
    return template(data)


def path_set(data: dict, *, path: str, value):
    parts = path.split('.')
    for key in parts[:-1]:
        data = data.setdefault(key, {})
    data[parts[-1]] = value


def path_delete(data: dict, *, path: str):
    parts = path.split('.')
    for key in parts[:-1]:
        try:
            data = data.get(key, None)
        except AttributeError:
            data = None

        if data is None:
            return

    del data[parts[-1]]


def transform_cast(value, *, datatype: typing.Literal['string', 'number', 'integer', 'float', 'boolean'] | None):
    match datatype:
        case 'string':
            return str(value)
        case 'integer':
            return int(value)
        case 'float' | 'number':
            num = float(value)
            return int(num) if num.is_integer() else num
        case 'boolean':
            return bool(value)
    return value
