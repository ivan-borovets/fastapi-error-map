import asyncio
import functools

import httpx
import pytest
from fastapi import FastAPI
from starlette import status

from fastapi_error_map import ErrorAwareRouter, RouteConfigError, rule, to_threadpool
from tests.factories import ClientError


def loop_running_here() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


async def test_runs_sync_on_error_inline_by_default(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/sync-on-error/"
    seen: dict[str, bool] = {}

    def record(_err: Exception) -> None:
        seen["in_loop"] = loop_running_here()

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_409_CONFLICT,
                on_error=record,
            ),
        },
    )
    async def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    await client.get(path)

    assert seen["in_loop"] is True


async def test_offloads_sync_on_error_to_threadpool(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/offloaded-on-error/"
    seen: dict[str, bool] = {}

    def record(_err: Exception) -> None:
        seen["in_loop"] = loop_running_here()

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_409_CONFLICT,
                on_error=to_threadpool(record),
            ),
        },
    )
    async def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    await client.get(path)

    assert seen["in_loop"] is False


async def test_offloads_router_level_on_error_to_threadpool(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    seen: dict[str, bool] = {}

    def record(_err: Exception) -> None:
        seen["in_loop"] = loop_running_here()

    router = ErrorAwareRouter(on_error=to_threadpool(record))
    path = "/router-offloaded/"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    async def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    await client.get(path)

    assert seen["in_loop"] is False


async def test_runs_async_on_error_inline(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/async-inline/"
    seen: dict[str, bool] = {}

    async def record(_err: Exception) -> None:
        seen["in_loop"] = loop_running_here()

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_409_CONFLICT,
                on_error=record,
            ),
        },
    )
    async def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    await client.get(path)

    assert seen["in_loop"] is True


async def test_awaits_partial_of_async_on_error(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/partial-async-on-error/"
    calls: list[str] = []

    class AsyncHook:
        async def __call__(self, _err: Exception) -> None:
            calls.append("async-callable")

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_409_CONFLICT,
                on_error=functools.partial(AsyncHook()),
            ),
        },
    )
    async def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    await client.get(path)

    assert calls == ["async-callable"]


def test_to_threadpool_rejects_async_on_error() -> None:
    async def record(_err: Exception) -> None: ...

    with pytest.raises(RouteConfigError):
        to_threadpool(record)


def test_to_threadpool_rejects_partial_of_async_on_error() -> None:
    class AsyncHook:
        async def __call__(self, _err: Exception) -> None: ...

    with pytest.raises(RouteConfigError):
        to_threadpool(functools.partial(AsyncHook()))


def test_to_threadpool_rejects_double_wrap() -> None:
    def record(_err: Exception) -> None: ...

    with pytest.raises(RouteConfigError):
        to_threadpool(to_threadpool(record))
