import json
import os


def load_workflow(name: str) -> dict:
    path = os.path.join(os.path.dirname(__file__), 'defs', name)
    path = path + '.json' if not path.endswith('.json') else path
    with open(path) as f:
        return json.load(f)
