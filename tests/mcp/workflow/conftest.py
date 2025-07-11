import pytest

from jotsu.mcp.workflow import WorkflowEngine


@pytest.fixture(scope='function', name='engine')
async def engine_fixture():
    return WorkflowEngine([])
