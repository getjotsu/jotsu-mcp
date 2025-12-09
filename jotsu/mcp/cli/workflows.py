import json
import os.path
import sys

import aiofiles
import click
import jsonc
from dotenv import load_dotenv

from jotsu.mcp.local import LocalMCPClient, LocalCredentialsManager
from jotsu.mcp.types import Workflow, slug, WorkflowResultNode, WorkflowMCPNode
from jotsu.mcp.workflow.engine import WorkflowEngine
from jotsu.mcp.workflow.sessions import WorkflowSessionManager

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

    workflow_id = id_ or slug()
    w = Workflow(id=workflow_id, name=name or workflow_id, description=description)
    w.nodes.append(WorkflowResultNode(id=slug()))

    async with aiofiles.open(path, 'w') as fp:
        await fp.write(w.model_dump_json(indent=4))

    display_name = f'{w.name} [{w.id}]' if w.id != w.name else w.id
    click.echo(f'Created workflow {display_name}: {path}')


@workflow.command()
@click.argument('path')
@click.option('--data', default=None, help='Initial data specified as JSON or as a path to a JSON file.')
@click.option('--no-format', is_flag=True, default=False)
@utils.async_cmd
async def run(path: str, no_format: bool, data: str):
    """Run a given workflow. """
    indent = None if no_format else 4

    if data:
        data = data.strip()
        if data.startswith('{'):
            data = json.loads(data)
        else:
            with open(data, 'r') as fp:
                data = jsonc.load(fp)

    async with aiofiles.open(path) as f:
        content = await f.read()

    w = Workflow(**jsonc.loads(content))

    engine = WorkflowEngine(w, client=LocalMCPClient())
    async for msg in engine.run_workflow(w.id, data):
        click.echo(json.dumps(msg, indent=indent))


@workflow.command()
@click.argument('path')
@click.option('--force', '-f', is_flag=True)
@utils.async_cmd
async def authenticate(path: str, force: bool):
    """Authenticate a workflow without actually running it. """
    credential_manager = LocalCredentialsManager(force=force)
    client = LocalMCPClient(credentials_manager=credential_manager)

    async with aiofiles.open(path) as f:
        content = await f.read()

    w = Workflow(**jsonc.loads(content))
    sessions = WorkflowSessionManager(w, client=client)

    async def _authenticate(name: str, session_id: str):
        click.echo(f'  {name} ...', nl=False)
        session = await sessions.get_session(session_id)
        await session.load()
        click.echo(f'\r  {name}: OK')

    if w.servers:
        click.echo(f'Servers [{len(w.servers)}]:')
        for server in w.servers:
            await _authenticate(server.name or server.id, server.id)

    if w.nodes:
        click.echo(f'Nodes [{len(w.nodes)}]:')
        for node in w.nodes:
            if isinstance(node, WorkflowMCPNode):
                await _authenticate(node.name or node.id, node.id)

    await sessions.aclose()
