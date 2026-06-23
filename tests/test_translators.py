import httpx
from fastapi import FastAPI
from starlette import status

from fastapi_error_map import ErrorAwareRouter, rule, structured
from tests.factories import (
    ChildError,
    MalformedError,
    ParentError,
    PlainError,
    ServerError,
    StructuredError,
)


async def test_structured_fills_code_message_details_for_4xx(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(translator_factory=structured())
    path = "/structured-4xx/"

    @router.get(
        path,
        error_map={
            StructuredError: status.HTTP_400_BAD_REQUEST,
        },
    )
    def boom() -> None:
        raise StructuredError(
            "bad",
            code="BAD_INPUT",
            details={"field": "x"},
        )

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert r.json() == {
        "code": "BAD_INPUT",
        "message": "bad",
        "details": {"field": "x"},
    }


async def test_structured_falls_back_to_status_name_without_code(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(translator_factory=structured())
    path = "/structured-no-code/"

    @router.get(
        path,
        error_map={
            PlainError: status.HTTP_404_NOT_FOUND,
        },
    )
    def boom() -> None:
        raise PlainError("missing")

    app.include_router(router)

    r = await client.get(path)

    assert r.json() == {"code": "HTTP_404_NOT_FOUND", "message": "missing"}


async def test_structured_falls_back_on_garbage_attribute_types(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(translator_factory=structured())
    path = "/structured-garbage/"

    @router.get(
        path,
        error_map={
            MalformedError: status.HTTP_409_CONFLICT,
        },
    )
    def boom() -> None:
        raise MalformedError("nope")

    app.include_router(router)

    r = await client.get(path)

    assert r.json() == {"code": "HTTP_409_CONFLICT", "message": "nope"}


async def test_structured_omits_details_when_absent(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(translator_factory=structured())
    path = "/structured-no-details/"

    @router.get(
        path,
        error_map={
            StructuredError: status.HTTP_400_BAD_REQUEST,
        },
    )
    def boom() -> None:
        raise StructuredError("x")

    app.include_router(router)

    r = await client.get(path)

    assert "details" not in r.json()


async def test_structured_omits_message_without_text(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(translator_factory=structured())
    path = "/structured-no-message/"

    @router.get(
        path,
        error_map={
            StructuredError: status.HTTP_400_BAD_REQUEST,
        },
    )
    def boom() -> None:
        raise StructuredError(code="OOPS")

    app.include_router(router)

    r = await client.get(path)

    assert r.json() == {"code": "OOPS"}


async def test_structured_per_field_extractor_overrides_default(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    factory = structured(code=lambda err: getattr(err, "error_code", None))
    router = ErrorAwareRouter(translator_factory=factory)
    path = "/structured-custom/"

    class CustomError(Exception):
        error_code = "CUSTOM"

    @router.get(
        path,
        error_map={
            CustomError: status.HTTP_400_BAD_REQUEST,
        },
    )
    def boom() -> None:
        raise CustomError("custom")

    app.include_router(router)

    r = await client.get(path)

    assert r.json() == {"code": "CUSTOM", "message": "custom"}


async def test_structured_keeps_5xx_opaque_by_default(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(translator_factory=structured())
    path = "/structured-5xx/"

    @router.get(
        path,
        error_map={
            ServerError: status.HTTP_503_SERVICE_UNAVAILABLE,
        },
    )
    def boom() -> None:
        raise ServerError("10.0.0.5")

    app.include_router(router)

    r = await client.get(path)

    body = r.json()
    assert body == {
        "code": "HTTP_503_SERVICE_UNAVAILABLE",
        "message": "Internal server error",
    }
    assert "10.0.0.5" not in r.text


async def test_structured_exposes_5xx_for_allowlisted_type(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    factory = structured(exposed_5xx_types=(ServerError,))
    router = ErrorAwareRouter(translator_factory=factory)
    path = "/structured-5xx-exposed/"

    @router.get(
        path,
        error_map={
            ServerError: status.HTTP_503_SERVICE_UNAVAILABLE,
        },
    )
    def boom() -> None:
        raise ServerError("upstream detail")

    app.include_router(router)

    r = await client.get(path)

    assert r.json() == {
        "code": "HTTP_503_SERVICE_UNAVAILABLE",
        "message": "upstream detail",
    }


async def test_structured_exposes_5xx_for_allowlisted_ancestor(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    factory = structured(exposed_5xx_types=(ParentError,))
    router = ErrorAwareRouter(translator_factory=factory)
    path = "/structured-5xx-ancestor/"

    @router.get(
        path,
        error_map={
            ChildError: status.HTTP_503_SERVICE_UNAVAILABLE,
        },
    )
    def boom() -> None:
        raise ChildError("upstream detail visible")

    app.include_router(router)

    r = await client.get(path)

    assert r.json()["message"] == "upstream detail visible"


async def test_structured_includes_details_when_empty_mapping(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(translator_factory=structured())
    path = "/structured-empty-details/"

    @router.get(
        path,
        error_map={
            StructuredError: status.HTTP_400_BAD_REQUEST,
        },
    )
    def boom() -> None:
        raise StructuredError("oops", code="OOPS", details={})

    app.include_router(router)

    r = await client.get(path)

    assert r.json() == {"code": "OOPS", "message": "oops", "details": {}}


async def test_structured_uses_unknown_name_for_nonstandard_status(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(translator_factory=structured())
    path = "/structured-nonstandard/"

    @router.get(
        path,
        error_map={
            PlainError: 450,
        },
    )
    def boom() -> None:
        raise PlainError("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.json()["code"] == "HTTP_450_UNKNOWN"


async def test_structured_uses_custom_server_message(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    factory = structured(server_message="Service unavailable")
    router = ErrorAwareRouter(translator_factory=factory)
    path = "/structured-5xx-msg/"

    @router.get(
        path,
        error_map={
            ServerError: status.HTTP_503_SERVICE_UNAVAILABLE,
        },
    )
    def boom() -> None:
        raise ServerError("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.json()["message"] == "Service unavailable"


async def test_simple_does_not_leak_5xx_message(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/simple-5xx/"

    @router.get(
        path,
        error_map={
            ServerError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )
    def boom() -> None:
        raise ServerError("secret")

    app.include_router(router)

    r = await client.get(path)

    assert r.json() == {"error": "Internal server error"}
    assert "secret" not in r.text


async def test_rule_translator_overrides_router_factory(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(translator_factory=structured())
    path = "/rule-translator/"

    @router.get(
        path,
        error_map={
            PlainError: rule(
                status.HTTP_418_IM_A_TEAPOT,
                translator=str,
            ),
        },
    )
    def boom() -> None:
        raise PlainError("brewing")

    app.include_router(router)

    r = await client.get(path)

    assert r.json() == "brewing"
