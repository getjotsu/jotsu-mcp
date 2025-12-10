import inspect
import json
import jsonata

from jotsu.mcp.types.models import WorkflowModelNode
from jotsu.mcp.workflow.utils import pybars_render


def get_messages(data: dict, prompt: str):
    messages = data.get('messages', None)
    if messages is None:
        messages = []

        # Don't use prompt from the messages, it can be constructed if needed using a template.
        if prompt:
            content = pybars_render(prompt, data)
            messages.append({
                'role': 'user',
                'content': content
            })
            data['prompt'] = content
    return messages


def update_data_from_json(data: dict, content: str | dict | object, *, node: WorkflowModelNode):
    json_data = json.loads(content) if isinstance(content, str) else content
    if node.member:
        node_data = data.get(node.member, {})
        node_data.update(json_data)
        data[node.member] = node_data
    else:
        data.update(json_data)


def update_data_from_text(data: dict, text: str, *, node: WorkflowModelNode):
    member = node.member or node.name
    result = data.get(node.member or node.name, '')
    if result:
        result += '\n'
    result += text
    data[member] = result


def is_async_generator(handler) -> bool:
    # handle both function and bound method
    func = getattr(handler, '__func__', handler)
    return inspect.isasyncgenfunction(func)


def is_result_or_complete_node(result: dict) -> bool:
    if result:
        node = result.get('node')
        if node:
            node_type = node.get('type')
            return node_type in ['result', 'complete']
    return False


def jsonata_value(data: dict, expr: str):
    expr = jsonata.Jsonata(expr)

    # The Python implementation doesn't contain the Eval functions, including $parse.
    expr.register_lambda('parse', lambda x: json.loads(x))

    return expr.evaluate(data)
