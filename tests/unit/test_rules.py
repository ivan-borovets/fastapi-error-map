from typing import Union

import pytest

from fastapi_error_map.rules import Rule, resolve_rule_for_error, rule
from tests.unit.error_stubs import DatabaseError, UnknownError, ValidationError
from tests.unit.translator_stubs import (
    CustomTranslator,
    DummyClientErrorTranslator,
    DummyServerErrorTranslator,
)

ErrorMap = dict[type[Exception], Union[int, Rule]]


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(400, id="short_form"),
        pytest.param(rule(status=400), id="full_form"),
    ],
)
def test_resolves_status_code_with_client_error_translator(
    rule: Union[int, Rule],
) -> None:
    sut = resolve_rule_for_error(
        error=ValidationError(),
        error_map={ValidationError: rule},
        default_client_error_translator=DummyClientErrorTranslator(),
        default_server_error_translator=DummyServerErrorTranslator(),
    )

    assert sut.status == 400
    assert isinstance(sut.translator, DummyClientErrorTranslator)


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(503, id="short_form"),
        pytest.param(rule(status=503), id="full_form"),
    ],
)
def test_resolves_status_code_with_server_error_translator(
    rule: Union[int, Rule],
) -> None:
    sut = resolve_rule_for_error(
        error=DatabaseError(),
        error_map={DatabaseError: rule},
        default_client_error_translator=DummyClientErrorTranslator(),
        default_server_error_translator=DummyServerErrorTranslator(),
    )

    assert sut.status == 503
    assert isinstance(sut.translator, DummyServerErrorTranslator)


def test_does_not_override_explicit_translator() -> None:
    custom_translator = CustomTranslator()

    sut = resolve_rule_for_error(
        error=ValidationError(),
        error_map={
            ValidationError: rule(status=400, translator=custom_translator),
        },
        default_client_error_translator=DummyClientErrorTranslator(),
        default_server_error_translator=DummyServerErrorTranslator(),
    )

    assert sut.status == 400
    assert sut.translator is custom_translator


def test_unmapped_error_raises_runtime_error() -> None:
    error = UnknownError()

    with pytest.raises(RuntimeError):
        resolve_rule_for_error(
            error=error,
            error_map={
                ValidationError: 400,
                DatabaseError: 503,
            },
            default_client_error_translator=DummyClientErrorTranslator(),
            default_server_error_translator=DummyServerErrorTranslator(),
            default_on_error=None,
        )
