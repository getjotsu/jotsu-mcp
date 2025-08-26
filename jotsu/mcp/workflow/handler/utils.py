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
