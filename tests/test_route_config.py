import httpx
import pytest
from fastapi import APIRouter, FastAPI
from starlette import status

from fastapi_error_map import ErrorAwareRoute, RouteConfigError, error_map
from tests.factories import ClientError


async def test_interop_via_route_class_and_decorator(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = APIRouter(route_class=ErrorAwareRoute)
    path = "/route-class-interop/"

    @router.get(path)
    @error_map({ClientError: status.HTTP_409_CONFLICT})
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_409_CONFLICT


def test_fails_when_function_decorated_twice_with_different_maps() -> None:
    @error_map({ClientError: status.HTTP_409_CONFLICT})
    def endpoint() -> None:
        raise ClientError("x")

    with pytest.raises(RouteConfigError):
        error_map({ClientError: status.HTTP_400_BAD_REQUEST})(endpoint)


async def test_allows_redecorating_with_an_equal_map(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = APIRouter(route_class=ErrorAwareRoute)
    path = "/redecorated/"

    @router.get(path)
    @error_map({ClientError: status.HTTP_409_CONFLICT})
    @error_map({ClientError: status.HTTP_409_CONFLICT})
    def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_409_CONFLICT
