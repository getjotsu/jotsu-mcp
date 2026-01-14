import inspect
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

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

###


def parse_utc(value: str) -> str:
    # Normalize Z → +00:00 for fromisoformat
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # JSONata works best with JSON-serializable values
    return dt.isoformat()


def to_tz(value: str, tz_name: str) -> str:
    dt = datetime.fromisoformat(value)

    if dt.tzinfo is None:
        raise ValueError('datetime must be timezone-aware')

    tz = ZoneInfo(tz_name)
    return dt.astimezone(tz).isoformat()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def jsonata_value(data: dict, expr: str):
    expr = jsonata.Jsonata(expr)

    # The Python implementation doesn't contain the Eval functions, including $parse.
    expr.register_lambda('parse', lambda x: json.loads(x))

    # Datetime helpers
    expr.register_lambda('parse_utc', lambda x: parse_utc(x))
    expr.register_lambda('to_tz', lambda x, y: to_tz(x, y))
    expr.register_lambda('now_utc', lambda: now_utc())

    return expr.evaluate(data)
