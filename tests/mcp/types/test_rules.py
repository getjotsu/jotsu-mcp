from jotsu.mcp.types import rules


def test_rules_any():
    rule = rules.AnyRule()
    assert rule.test(42)
    assert rule.test(False) is True


def test_rules_gt():
    rule = rules.GreaterThanRule(value=2)
    assert rule.test(3)
    assert rule.test(2) is False


def test_rules_lt():
    rule = rules.LessThanRule(value=2)
    assert rule.test(3) is False
    assert rule.test(2) is False
    assert rule.test(1)


def test_rules_gte():
    rule = rules.GreaterThanEqualRule(value=2)
    assert rule.test(3)
    assert rule.test(2)
    assert rule.test(.5) is False


def test_rules_lte():
    rule = rules.LessThanEqualRule(value=2)
    assert rule.test(3) is False
    assert rule.test(2)
    assert rule.test(.5)


def test_rules_eq():
    rule = rules.EqualRule(value=2)
    assert rule.test(3) is False
    assert rule.test(2)
    assert rule.test(.5) is False


def test_rules_neq():
    rule = rules.NotEqualRule(value=2)
    assert rule.test(3)
    assert rule.test(2) is False
    assert rule.test(.5)


def test_rules_between():
    rule = rules.BetweenRule(value=2, value2=4)
    assert rule.test(3)
    assert rule.test(2)
    assert rule.test(.5) is False


def test_rules_contains():
    rule = rules.ContainsRule(value=2)
    assert rule.test(['a', 2])
    assert rule.test([]) is False


def test_rules_regex_match():
    rule = rules.RegexMatchRule(value='Xa+')
    assert rule.test('Xa123')
    assert rule.test('xXa') is False

    rule = rules.RegexMatchRule(value='^Xa+$')
    assert rule.test('Xaa')
    assert rule.test('Xa123') is False


def test_rules_regex_search():
    rule = rules.RegexSearchRule(value='Xa+')
    assert rule.test('Xa123')
    assert rule.test('xXa')

    rule = rules.RegexSearchRule(value='^Xa+$')
    assert rule.test('1Xaa') is False
    assert rule.test('Xa123') is False
    assert rule.test('Xaa')


def test_rules_truthy():
    rule = rules.TruthyRule()
    assert rule.test('abc')
    assert rule.test({}) is False


def test_rules_falsy():
    rule = rules.FalsyRule()
    assert rule.test([])
