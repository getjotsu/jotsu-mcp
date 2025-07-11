import json
import os.path
import sys

import aiofiles
import click
from dotenv import load_dotenv

from jotsu.mcp.local import LocalMCPClient
from jotsu.mcp.types import Workflow, WorkflowEvent
from jotsu.mcp.workflow.engine import WorkflowEngine

from .base import cli
from . import utils

load_dotenv()


@cli.group('workflow')
def workflow():
    pass


@workflow.command()
@click.argument('path', default=None, required=False)
@click.option('--id', 'id_', default=None)
@click.option('--name', default=None)
@click.option('--description', default=None)
@click.option('--force', '-f', is_flag=True)
@utils.async_cmd
async def init(path: str, id_: str, name: str, description: str, force: bool):
    """Create a mostly-empty workflow in 'path'. """
    path = os.path.abspath(path if path else './workflow.json')

    if os.path.exists(path) and not force:
        if not click.confirm('That workflow already exists, overwrite?'):
            click.echo('canceled.')
            sys.exit(0)

    workflow_id = id_ or utils.ulid()
    flow = Workflow(id=workflow_id, name=name or workflow_id, description=description)

    flow.event = WorkflowEvent(name='Manual', type='manual')

    async with aiofiles.open(path, 'w') as fp:
        await fp.write(flow.model_dump_json(indent=4))

    display_name = f'{flow.name} [{flow.id}]' if flow.id != flow.name else flow.id
    click.echo(f'Created workflow {display_name}: {path}')


@workflow.command()
@click.argument('path')
@click.option('--no-format', is_flag=True, default=False)
@utils.async_cmd
async def run(path: str, no_format: bool):
    """Run a given workflow. """
    indent = None if no_format else 4

    async with aiofiles.open(path) as f:
        content = await f.read()
    flow = Workflow(**json.loads(content))

    engine = WorkflowEngine(flow, client=LocalMCPClient())
    async for msg in engine.run_workflow(flow.id):
        click.echo(json.dumps(msg, indent=indent))
