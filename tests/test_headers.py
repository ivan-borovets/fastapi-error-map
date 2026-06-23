from collections.abc import Mapping

import httpx
import pytest
from fastapi import FastAPI
from starlette import status

from fastapi_error_map import ErrorAwareRouter, Headers, rule
from tests.factories import ClientError


async def test_applies_static_headers(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/static-headers/"

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

    r = await client.get(path)

    assert r.headers["WWW-Authenticate"] == "Bearer"


async def test_computes_dynamic_headers_from_exception(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/dynamic-headers/"

    def retry_after(err: Exception) -> Mapping[str, str]:
        return {"Retry-After": str(getattr(err, "retry_after", 60))}

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_429_TOO_MANY_REQUESTS,
                headers=retry_after,
            ),
        },
    )
    def boom() -> None:
        err = ClientError("slow down")
        err.retry_after = 120  # type: ignore[attr-defined]
        raise err

    app.include_router(router)

    r = await client.get(path)

    assert r.headers["Retry-After"] == "120"


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({"Retry-After": "30"}, id="static"),
        pytest.param(lambda _err: {"Retry-After": "30"}, id="dynamic"),
    ],
)
async def test_headers_pass_through_on_5xx_while_body_stays_opaque(
    headers: Headers,
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/headers-5xx/"

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                headers=headers,
            ),
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.json() == {"error": "Internal server error"}
    assert r.headers["Retry-After"] == "30"


async def test_content_type_header_overrides_json_default(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/problem-content-type/"

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_409_CONFLICT,
                headers={"Content-Type": "application/problem+json"},
            ),
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.headers["content-type"] == "application/problem+json"
