from asteval import Interpreter


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
    return aeval(wrap_function(expr))


def pybars_compiler():  # pragma: no coverage
    if not hasattr(pybars_compiler, '_compiler'):
        from pybars import Compiler
        setattr(pybars_compiler, '_compiler', Compiler())
    return getattr(pybars_compiler, '_compiler')


def pybars_render(source: str, data: any) -> str:
    compiler = pybars_compiler()
    template = compiler.compile(source)
    return template(source, data)
