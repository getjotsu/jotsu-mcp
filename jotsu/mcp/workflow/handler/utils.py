import json
import jsonata

from jotsu.mcp.types.models import WorkflowModelNode
from jotsu.mcp.workflow.utils import pybars_render


def get_messages(data: dict, prompt: str):
    messages = data.get('messages', None)
    if messages is None:
        messages = []
        prompt = data.get('prompt', prompt)
        if prompt:
            messages.append({
                'role': 'user',
                'content': pybars_render(prompt, data)
            })
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
    result += text
    data[member] = result


def jsonata_value(data: dict, expr: str):
    expr = jsonata.Jsonata(expr)
    return expr.evaluate(data)
