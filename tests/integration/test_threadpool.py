import asyncio
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI

from fastapi_error_map import ErrorAwareRouter, rule
from tests.integration.conftest import AsgiClientFactory

if TYPE_CHECKING:
    import httpx


def has_running_loop_in_this_thread() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


@pytest.mark.asyncio
async def test_fastapi_sync_handler_runs_in_threadpool(
    app: FastAPI,
    asgi_client_factory: AsgiClientFactory,
) -> None:
    @app.get("/")
    def index():
        return {"in_loop": has_running_loop_in_this_thread()}

    async with asgi_client_factory(app) as client:
        index_response: httpx.Response = await client.get("/")

    assert index_response.status_code == 200
    assert index_response.json() == {"in_loop": False}


@pytest.mark.asyncio
async def test_error_aware_router_sync_handler_runs_in_threadpool(
    app: FastAPI,
    asgi_client_factory: AsgiClientFactory,
) -> None:
    router = ErrorAwareRouter()

    @app.get("/")
    def index():
        return {"in_loop": has_running_loop_in_this_thread()}

    app.include_router(router)

    async with asgi_client_factory(app) as client:
        index_response: httpx.Response = await client.get("/")

    assert index_response.status_code == 200
    assert index_response.json() == {"in_loop": False}


@pytest.mark.asyncio
async def test_error_aware_router_sync_on_error_runs_in_threadpool(
    app: FastAPI,
    asgi_client_factory: AsgiClientFactory,
) -> None:
    router = ErrorAwareRouter()
    seen: dict[str, bool] = {}

    def on_error(_: Exception) -> None:
        seen["in_loop"] = has_running_loop_in_this_thread()

    @router.get("/err", error_map={ValueError: rule(status=400, on_error=on_error)})
    def index():
        raise ValueError

    app.include_router(router)

    async with asgi_client_factory(app) as client:
        index_response: httpx.Response = await client.get("/err")

    assert index_response.status_code == 400
    assert seen["in_loop"] is False
