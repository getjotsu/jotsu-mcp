from jotsu.mcp.workflow.handler import utils


def test_update_data_from_json(mocker):
    data = {}
    utils.update_data_from_json(data, {'foo': 'baz'}, node=mocker.Mock(member='bar'))
    assert data == {'bar': {'foo': 'baz'}}


def test_is_result_or_complete_node():
    assert utils.is_result_or_complete_node({}) is False


def test_get_messages():
    assert utils.get_messages({}, 'xxx') == [{'role': 'user', 'content': 'xxx'}]


def test_jsonata_value_parse():
    data = {'a': '{"b": 1}'}
    assert utils.jsonata_value(data, '$parse(a)') == {'b': 1}
