from jotsu.mcp.workflow.handler.utils import update_data_from_json


def test_update_data_from_json(mocker):
    data = {}
    update_data_from_json(data, {'foo': 'baz'}, node=mocker.Mock(member='bar'))
    assert data == {'bar': {'foo': 'baz'}}
