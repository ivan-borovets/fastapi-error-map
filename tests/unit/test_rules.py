from typing import Union

import pytest
from starlette import status

from fastapi_error_map.rules import Rule, resolve_rule_for_error, rule
from tests.unit.error_stubs import DatabaseError, UnknownError, ValidationError
from tests.unit.translator_stubs import (
    CustomTranslator,
    DummyClientErrorTranslator,
    DummyServerErrorTranslator,
)

ErrorMap = dict[type[Exception], Union[int, Rule]]


class ParentError(Exception):
    pass


class ChildError(ParentError):
    pass


class OtherParentError(Exception):
    pass


class MultipleInheritanceError(ChildError, OtherParentError):
    pass


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


@pytest.mark.parametrize(
    "bad_status",
    [
        status.HTTP_200_OK,
        status.HTTP_300_MULTIPLE_CHOICES,
        status.WS_1000_NORMAL_CLOSURE,
    ],
)
def test_resolver_rejects_non_error_status_codes(bad_status: int) -> None:
    with pytest.raises(RuntimeError):
        resolve_rule_for_error(
            error=ValidationError(),
            error_map={ValidationError: bad_status},
            default_client_error_translator=DummyClientErrorTranslator(),
            default_server_error_translator=DummyServerErrorTranslator(),
            default_on_error=None,
        )


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


def test_resolves_child_over_parent() -> None:
    sut = resolve_rule_for_error(
        error=ChildError(),
        error_map={
            ParentError: 400,
            ChildError: 409,
        },
        default_client_error_translator=DummyClientErrorTranslator(),
        default_server_error_translator=DummyServerErrorTranslator(),
    )

    assert sut.status == 409


def test_falls_back_to_parent_when_child_missing() -> None:
    sut = resolve_rule_for_error(
        error=ChildError(),
        error_map={
            ParentError: 400,
        },
        default_client_error_translator=DummyClientErrorTranslator(),
        default_server_error_translator=DummyServerErrorTranslator(),
    )

    assert sut.status == 400


def test_multiple_inheritance_prefers_first_match_in_mro() -> None:
    sut = resolve_rule_for_error(
        error=MultipleInheritanceError(),
        error_map={
            OtherParentError: 402,
            ChildError: 409,
        },
        default_client_error_translator=DummyClientErrorTranslator(),
        default_server_error_translator=DummyServerErrorTranslator(),
    )

    assert sut.status == 409


def test_does_not_resolve_base_exception_subclasses() -> None:
    with pytest.raises(RuntimeError):
        resolve_rule_for_error(
            error=KeyboardInterrupt(),  # type: ignore
            error_map={},
            default_client_error_translator=DummyClientErrorTranslator(),
            default_server_error_translator=DummyServerErrorTranslator(),
        )
