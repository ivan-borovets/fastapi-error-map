from typing import TYPE_CHECKING

from fastapi_error_map.openapi import build_openapi_responses
from fastapi_error_map.rules import rule
from tests.unit.error_stubs import DatabaseError, ValidationError
from tests.unit.translator_stubs import (
    ClientErrorStub,
    CustomTranslator,
    DummyClientErrorTranslator,
    DummyServerErrorTranslator,
    ServerErrorStub,
)

if TYPE_CHECKING:
    from fastapi_error_map.rules import ErrorMap


def test_builds_response_from_short_form_rule() -> None:
    error_map: ErrorMap = {
        ValidationError: 400,
        DatabaseError: 503,
    }

    responses = build_openapi_responses(
        error_map=error_map,
        default_client_error_translator=DummyClientErrorTranslator(),
        default_server_error_translator=DummyServerErrorTranslator(),
    )

    assert responses == {
        400: {"model": ClientErrorStub},
        503: {"model": ServerErrorStub},
    }


def test_builds_response_from_full_form_rule() -> None:
    error_map: ErrorMap = {
        ValidationError: rule(status=400),
        DatabaseError: rule(status=503),
    }

    responses = build_openapi_responses(
        error_map=error_map,
        default_client_error_translator=DummyClientErrorTranslator(),
        default_server_error_translator=DummyServerErrorTranslator(),
    )

    assert responses == {
        400: {"model": ClientErrorStub},
        503: {"model": ServerErrorStub},
    }


def test_builds_response_with_custom_translator() -> None:
    error_map: ErrorMap = {
        ValidationError: rule(status=400, translator=CustomTranslator()),
    }

    responses = build_openapi_responses(
        error_map=error_map,
        default_client_error_translator=DummyClientErrorTranslator(),
        default_server_error_translator=DummyServerErrorTranslator(),
    )

    assert responses == {400: {"model": dict}}
