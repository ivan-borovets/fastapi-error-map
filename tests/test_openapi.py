import functools
import warnings
from typing import Any, Final

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette import status

from fastapi_error_map import ErrorAwareRouter, ErrorMapWarning, Translator, rule
from tests.factories import (
    ClientError,
    OtherClientError,
    PlainError,
    TeapotResponse,
    other,
    teapot,
)

OPENAPI_URL: Final[str] = "/openapi.json"
# Literal, not status.HTTP_422_*: that constant is renamed across starlette versions.
HTTP_422_VALIDATION: Final[int] = 422


def responses_for(
    openapi: dict[str, Any],
    path: str,
    status_code: int,
) -> dict[str, Any]:
    responses = openapi["paths"][path]["get"]["responses"]
    return responses[str(status_code)]  # type: ignore[no-any-return]


async def test_documents_declared_status_in_openapi(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/documented/"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    response = await client.get(OPENAPI_URL)
    schema = response.json()

    assert str(status.HTTP_409_CONFLICT) in schema["paths"][path]["get"]["responses"]


@pytest.mark.parametrize(
    "translator",
    [
        pytest.param(teapot, id="plain"),
        pytest.param(functools.partial(teapot), id="partial"),
    ],
)
async def test_derives_model_from_translator_annotation(
    translator: Translator[TeapotResponse],
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/annotated/"

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_418_IM_A_TEAPOT,
                translator=translator,
            ),
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    response = await client.get(OPENAPI_URL)
    schema = response.json()
    entry = responses_for(schema, path, status.HTTP_418_IM_A_TEAPOT)

    ref = entry["content"]["application/json"]["schema"]
    assert ref["$ref"].endswith("TeapotResponse")


async def test_uses_openapi_model_override(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/lambda-model/"

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_418_IM_A_TEAPOT,
                translator=lambda err: {"reason": str(err)},
                openapi_model=TeapotResponse,
            ),
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    response = await client.get(OPENAPI_URL)
    schema = response.json()
    entry = responses_for(schema, path, status.HTTP_418_IM_A_TEAPOT)

    assert entry["content"]["application/json"]["schema"]["$ref"].endswith(
        "TeapotResponse",
    )


async def test_renders_anyof_for_two_models_on_one_status(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/anyof/"

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_400_BAD_REQUEST,
                translator=teapot,
            ),
            OtherClientError: rule(
                status.HTTP_400_BAD_REQUEST,
                translator=other,
            ),
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    response = await client.get(OPENAPI_URL)
    schema = response.json()
    entry = responses_for(schema, path, status.HTTP_400_BAD_REQUEST)

    assert "anyOf" in entry["content"]["application/json"]["schema"]


async def test_collapses_to_single_ref_for_two_rules_with_same_model(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/same-model/"

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_400_BAD_REQUEST,
                translator=teapot,
            ),
            OtherClientError: rule(
                status.HTTP_400_BAD_REQUEST,
                translator=teapot,
            ),
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    response = await client.get(OPENAPI_URL)
    schema = response.json()
    entry = responses_for(schema, path, status.HTTP_400_BAD_REQUEST)
    error_schema = entry["content"]["application/json"]["schema"]

    assert "anyOf" not in error_schema
    assert error_schema["$ref"].endswith("TeapotResponse")


async def test_user_supplied_responses_override_generated_entry(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/responses-override/"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
        responses={status.HTTP_409_CONFLICT: {"description": "USER OVERRIDE"}},
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    response = await client.get(OPENAPI_URL)
    schema = response.json()
    entry = responses_for(schema, path, status.HTTP_409_CONFLICT)

    assert entry == {"description": "USER OVERRIDE"}


async def test_does_not_document_dynamic_headers_in_openapi(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/dynamic-headers-doc/"

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_429_TOO_MANY_REQUESTS,
                headers=lambda _err: {"Retry-After": "30"},
            ),
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    response = await client.get(OPENAPI_URL)
    schema = response.json()
    entry = responses_for(schema, path, status.HTTP_429_TOO_MANY_REQUESTS)

    assert "headers" not in entry


async def test_documents_static_headers_in_openapi(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/headers-doc/"

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            ),
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    response = await client.get(OPENAPI_URL)
    schema = response.json()
    entry = responses_for(schema, path, status.HTTP_401_UNAUTHORIZED)

    assert "WWW-Authenticate" in entry["headers"]


async def test_documents_examples_in_openapi(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/examples/"
    example = {"limited": {"value": {"error": "later"}}}

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_429_TOO_MANY_REQUESTS, openapi_examples=example
            ),
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    response = await client.get(OPENAPI_URL)
    schema = response.json()
    entry = responses_for(schema, path, status.HTTP_429_TOO_MANY_REQUESTS)

    assert "limited" in entry["content"]["application/json"]["examples"]


async def test_uses_explicit_rule_description(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/description/"

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_409_CONFLICT,
                openapi_description="Order already cancelled.",
            ),
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    response = await client.get(OPENAPI_URL)
    schema = response.json()
    entry = responses_for(schema, path, status.HTTP_409_CONFLICT)

    assert entry["description"] == "Order already cancelled."


def test_warns_when_mapping_422_on_validated_route() -> None:
    router = ErrorAwareRouter()

    def boom(item_id: int) -> None:
        raise PlainError("x")

    declare = router.get(
        "/warn-422/",
        error_map={
            PlainError: HTTP_422_VALIDATION,
        },
    )

    with pytest.warns(ErrorMapWarning):
        declare(boom)


def test_does_not_warn_for_non_422_status() -> None:
    router = ErrorAwareRouter()

    def boom(item_id: int) -> None:
        raise PlainError("x")

    declare = router.get(
        "/no-warn/",
        error_map={
            PlainError: status.HTTP_400_BAD_REQUEST,
        },
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error", ErrorMapWarning)
        declare(boom)


def test_does_not_warn_for_422_on_route_without_params() -> None:
    router = ErrorAwareRouter()

    def boom() -> None:
        raise PlainError("x")

    declare = router.get(
        "/no-params/",
        error_map={
            PlainError: HTTP_422_VALIDATION,
        },
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error", ErrorMapWarning)
        declare(boom)


def test_warns_on_duplicate_example_keys_for_one_status() -> None:
    router = ErrorAwareRouter()
    shared = {"ex": {"value": {"error": "x"}}}

    def boom() -> None:
        raise ClientError("x")

    declare = router.get(
        "/dup-examples/",
        error_map={
            ClientError: rule(
                status.HTTP_400_BAD_REQUEST,
                openapi_examples=shared,
            ),
            OtherClientError: rule(
                status.HTTP_400_BAD_REQUEST,
                openapi_examples=shared,
            ),
        },
    )

    with pytest.warns(ErrorMapWarning, match="duplicate OpenAPI example key"):
        declare(boom)


@pytest.mark.parametrize(
    "framework_exc",
    [
        pytest.param(HTTPException, id="http-exception"),
        pytest.param(RequestValidationError, id="request-validation-error"),
    ],
)
def test_warns_when_mapping_a_framework_exception(
    framework_exc: type[Exception],
) -> None:
    router = ErrorAwareRouter()

    def boom() -> None:
        raise PlainError("x")

    declare = router.get(
        "/maps-framework-exc/",
        error_map={
            framework_exc: status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )

    with pytest.warns(ErrorMapWarning):
        declare(boom)
