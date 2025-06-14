import errno
import json
import logging
import sys
from contextlib import asynccontextmanager

from jotsu.mcp.client.client import LocalMCPClient
from jotsu.mcp.client.credentials import LocalCredentialsManager
from jotsu.mcp.workflow.models import Workflow, WorkflowServer
from jotsu.mcp.workflow.server import WorkflowEngine

try:
    # noinspection PyUnresolvedReferences
    import click
except ImportError:
    print("Package 'click' not found.  Did you install 'jotsu-mcp[cli]'?")
    sys.exit(errno.ENOENT)

import aiofiles

from . import utils

CREDENTIALS = 'credentials'


@asynccontextmanager
async def client_session(ctx, server: WorkflowServer):
    client = LocalMCPClient(credentials_manager=ctx.obj[CREDENTIALS])
    async with client.session(server) as session:
        yield session


@click.group()
@click.option('--store-path', default='~/.jotsu')
@click.option('--log-level', default='WARNING')
@click.pass_context
def cli(ctx, store_path, log_level):
    logging.basicConfig(level=log_level)
    ctx.ensure_object(dict)
    ctx.obj[CREDENTIALS] = LocalCredentialsManager(store_path)


@cli.command()
@click.argument('path')
@utils.async_cmd
async def workflow(path: str):
    """Run a given workflow. """

    async with aiofiles.open(path) as f:
        content = await f.read()
    flow = Workflow(**json.loads(content))

    engine = WorkflowEngine(flow, client=LocalMCPClient())
    res = await engine.run_workflow(flow.id)
    click.echo(res)


if __name__ == '__main__':
    cli()
