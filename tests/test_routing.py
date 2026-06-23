from typing import Final

import httpx
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from starlette import status

from fastapi_error_map import (
    ErrorAwareRoute,
    ErrorAwareRouter,
    RouteConfigError,
    rule,
)
from tests.factories import ClientError, ServerError

METHODS: Final[tuple[str, ...]] = (
    "get",
    "put",
    "post",
    "delete",
    "options",
    "head",
    "patch",
    "trace",
)


@pytest.mark.parametrize(
    "method",
    [pytest.param(m, id=m) for m in METHODS],
)
async def test_maps_error_for_every_http_method(
    method: str,
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/m/"

    def boom() -> None:
        raise ClientError("x")

    getattr(router, method)(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )(boom)
    app.include_router(router)

    r = await client.request(method.upper(), path)

    assert r.status_code == status.HTTP_409_CONFLICT
    if method != "head":
        assert r.json() == {"error": "x"}


async def test_maps_error_via_api_route(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/api-route/"

    @router.api_route(
        path,
        methods=["GET"],
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_409_CONFLICT


async def test_plain_route_works_without_error_map(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/plain/"

    @router.get(path)
    def ok() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_200_OK
    assert r.json() == {"status": "ok"}


async def test_applies_router_level_error_map(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(
        error_map={
            ServerError: status.HTTP_503_SERVICE_UNAVAILABLE,
        },
    )
    path = "/router-map/"

    @router.get(path)
    def boom() -> None:
        raise ServerError("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


async def test_route_error_map_wins_over_router_for_same_exception(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(
        error_map={
            ClientError: status.HTTP_400_BAD_REQUEST,
        },
    )
    path = "/override-key/"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_409_CONFLICT


@pytest.mark.parametrize(
    ("raised", "expected_status"),
    [
        pytest.param(
            ServerError,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            id="from-router-level-map",
        ),
        pytest.param(
            ClientError,
            status.HTTP_409_CONFLICT,
            id="from-route-level-map",
        ),
    ],
)
async def test_router_and_route_maps_both_apply(
    raised: type[Exception],
    expected_status: int,
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(
        error_map={
            ServerError: status.HTTP_503_SERVICE_UNAVAILABLE,
        },
    )
    path = "/merged/"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def boom() -> None:
        raise raised("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == expected_status


async def test_rule_on_error_overrides_router_on_error(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    calls: list[str] = []
    router = ErrorAwareRouter(on_error=lambda _err: calls.append("router"))
    path = "/on-error/"

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_409_CONFLICT,
                on_error=lambda _err: calls.append("rule"),
            ),
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    await client.get(path)

    assert calls == ["rule"]


async def test_router_on_error_fires_without_rule_level_hook(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    calls: list[str] = []
    router = ErrorAwareRouter(on_error=lambda _err: calls.append("router"))
    path = "/router-on-error/"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    await client.get(path)

    assert calls == ["router"]


async def test_preserves_map_through_nested_include_router(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    inner = ErrorAwareRouter()

    @inner.get(
        "/leaf/",
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def boom() -> None:
        raise ClientError("x")

    outer = APIRouter()
    outer.include_router(inner, prefix="/inner")
    app.include_router(outer, prefix="/api")

    r = await client.get("/api/inner/leaf/")

    assert r.status_code == status.HTTP_409_CONFLICT


async def test_nested_router_does_not_inherit_outer_policy(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    outer = ErrorAwareRouter(
        error_map={
            ServerError: status.HTTP_503_SERVICE_UNAVAILABLE,
        },
    )
    inner = ErrorAwareRouter()

    @inner.get(
        "/leaf/",
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def boom() -> None:
        raise ServerError("x")

    outer.include_router(inner)
    app.include_router(outer)

    with pytest.raises(ServerError):
        await client.get("/leaf/")


def test_websocket_rejects_error_map() -> None:
    router = ErrorAwareRouter()

    with pytest.raises(RouteConfigError):
        router.websocket(
            "/ws/",
            error_map={
                ClientError: status.HTTP_409_CONFLICT,
            },
        )


def test_rejects_route_class_that_skips_interception() -> None:
    with pytest.raises(RouteConfigError):
        ErrorAwareRouter(route_class=APIRoute)


async def test_accepts_route_class_subclassing_error_aware_route(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    class TracingRoute(ErrorAwareRoute): ...

    router = ErrorAwareRouter(route_class=TracingRoute)
    path = "/custom-route/"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_409_CONFLICT
