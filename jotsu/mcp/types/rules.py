import re
import typing

import pydantic

# noinspection SpellCheckingInspection
type RuleType = typing.Literal[
    'any',
    'gt', 'lt', 'gte', 'lte', 'eq', 'neq',
    'between', 'contains',
    'regex', 'truthy', 'falsy',
    'any',
]


class AnyRule(pydantic.BaseModel):
    type: typing.Literal['any'] = 'any'

    @staticmethod
    def test(_: any) -> bool:
        return True


class GreaterThanRule(pydantic.BaseModel):
    type: typing.Literal['gt'] = 'gt'
    value: int | float

    def test(self, value: int | float) -> bool:
        return value > self.value


class GreaterThanEqualRule(pydantic.BaseModel):
    type: typing.Literal['gte'] = 'gte'
    value: int | float

    def test(self, value: int | float) -> bool:
        return value >= self.value


class LessThanRule(pydantic.BaseModel):
    type: typing.Literal['lt'] = 'lt'
    value: int | float

    def test(self, value: int | float) -> bool:
        return value < self.value


class LessThanEqualRule(pydantic.BaseModel):
    type: typing.Literal['lte'] = 'lte'
    value: int | float

    def test(self, value: int | float) -> bool:
        return value <= self.value


class EqualRule(pydantic.BaseModel):
    type: typing.Literal['eq'] = 'eq'
    value: typing.Any

    def test(self, value: typing.Any) -> bool:
        return value == self.value


class NotEqualRule(pydantic.BaseModel):
    type: typing.Literal['neq'] = 'neq'
    value: typing.Any

    def test(self, value: int | float) -> bool:
        return value != self.value


class BetweenRule(pydantic.BaseModel):
    type: typing.Literal['between'] = 'between'
    value: int | float
    value2: int | float

    def test(self, value: int | float) -> bool:
        return self.value <= value <= self.value2


class ContainsRule(pydantic.BaseModel):
    type: typing.Literal['contains'] = 'contains'
    value: typing.Any

    def test(self, value: typing.List[typing.Any]) -> bool:
        return self.value in value


class RegexMatchRule(pydantic.BaseModel):
    type: typing.Literal['match'] = 'match'
    value: str  # pattern

    def test(self, value: str) -> bool:
        return bool(re.match(self.value, value))


class RegexSearchRule(pydantic.BaseModel):
    type: typing.Literal['search'] = 'search'
    value: str  # pattern

    def test(self, value: str) -> bool:
        return bool(re.search(self.value, value))


class TruthyRule(pydantic.BaseModel):
    type: typing.Literal['truthy'] = 'truthy'

    @staticmethod
    def test(value: typing.Any) -> bool:
        return bool(value)


class FalsyRule(pydantic.BaseModel):
    type: typing.Literal['false'] = 'falsy'

    @staticmethod
    def test(value: typing.Any) -> bool:
        return not bool(value)


type Rule = (
    AnyRule |
    GreaterThanRule | LessThanRule | GreaterThanEqualRule | LessThanEqualRule |
    EqualRule | NotEqualRule | BetweenRule | ContainsRule | RegexMatchRule | RegexSearchRule |
    TruthyRule | FalsyRule
)
