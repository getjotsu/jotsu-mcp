import logging
import click

from jotsu.mcp.local import LocalCredentialsManager

from .utils import CREDENTIALS


@click.group()
@click.option('--store-path', default='~/.jotsu')
@click.option('--log-level', default='WARNING')
@click.option('--log-format', default=None)
@click.pass_context
def cli(ctx, store_path, log_level, log_format):
    logging.basicConfig(format=log_format)
    logger = logging.getLogger('jotsu')
    logger.setLevel(level=log_level)

    ctx.ensure_object(dict)
    ctx.obj[CREDENTIALS] = LocalCredentialsManager(store_path)
