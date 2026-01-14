from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

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


def test_jsonata_value_parse_utc():
    data = {}
    result = utils.jsonata_value(data, "$parse_utc('2026-01-13T14:30:00')")

    dt = datetime.fromisoformat(result)
    assert dt.tzinfo is not None
    assert dt.utcoffset() == timezone.utc.utcoffset(None)
    assert dt.isoformat() == '2026-01-13T14:30:00+00:00'


def test_jsonata_value_to_tz():
    data = {}
    result = utils.jsonata_value(
        data,
        "$to_tz($parse_utc('2026-01-13T14:30:00Z'), 'America/Los_Angeles')",
    )

    dt = datetime.fromisoformat(result)
    assert dt.tzinfo is not None

    expected = datetime(2026, 1, 13, 14, 30, tzinfo=timezone.utc).astimezone(
        ZoneInfo('America/Los_Angeles')
    )
    assert dt.isoformat() == expected.isoformat()


def test_jsonata_value_now_utc():
    data = {}
    before = datetime.now(timezone.utc)
    result = utils.jsonata_value(data, '$now_utc()')
    after = datetime.now(timezone.utc)

    dt = datetime.fromisoformat(result)
    assert dt.tzinfo is not None
    assert dt.utcoffset() == timezone.utc.utcoffset(None)
    assert before <= dt <= after


def test_jsonata_value_to_tz_naive_datetime_raises():
    # No timezone info in the ISO string
    expr = "$to_tz('2026-01-13T14:30:00', 'America/Los_Angeles')"

    with pytest.raises(ValueError, match='datetime must be timezone-aware'):
        utils.jsonata_value({}, expr)
