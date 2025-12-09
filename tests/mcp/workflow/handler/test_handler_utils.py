from jotsu.mcp.workflow.handler.utils import update_data_from_json, is_result_or_complete_node, get_messages


def test_update_data_from_json(mocker):
    data = {}
    update_data_from_json(data, {'foo': 'baz'}, node=mocker.Mock(member='bar'))
    assert data == {'bar': {'foo': 'baz'}}


def test_is_result_or_complete_node():
    assert is_result_or_complete_node({}) is False


def test_get_messages():
    assert get_messages({}, 'xxx') == [{'role': 'user', 'content': 'xxx'}]
