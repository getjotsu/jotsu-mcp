import errno
import sys

try:
    import click   # noqa
except ImportError:
    print("Package 'click' not found.  Did you install 'jotsu-mcp[cli]'?")
    sys.exit(errno.ENOENT)

from .base import cli

from . import workflows  # noqa


if __name__ == '__main__':
    cli()
