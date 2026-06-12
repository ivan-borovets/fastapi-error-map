import asyncio
import logging

import httpx
import pytest
from fastapi import Depends, FastAPI, HTTPException
from starlette import status

from fastapi_error_map import ErrorAwareRouter, rule
from tests.factories import ChildError, ClientError, ParentError, PlainError


async def test_maps_exception_to_declared_status(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/boom/"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def boom() -> None:
        raise ClientError("nope")

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_409_CONFLICT
    assert r.json() == {"error": "nope"}


async def test_passes_http_exception_through_when_error_map_present(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/http-exc/"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def http_exc() -> None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="passthrough",
        )

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_404_NOT_FOUND
    assert r.json() == {"detail": "passthrough"}


async def test_reraises_unmapped_exception_as_original(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/unmapped/"
    message = "not in the map"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def unmapped() -> None:
        raise PlainError(message)

    app.include_router(router)

    with pytest.raises(PlainError, match=message):
        await client.get(path)


async def test_logs_unmapped_exception_by_default(
    app: FastAPI,
    client: httpx.AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    router = ErrorAwareRouter()
    path = "/unmapped-warn/"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def unmapped() -> None:
        raise PlainError("x")

    app.include_router(router)

    with (
        caplog.at_level(logging.WARNING, logger="fastapi_error_map"),
        pytest.raises(PlainError),
    ):
        await client.get(path)

    assert any("PlainError" in record.message for record in caplog.records)


async def test_stays_silent_on_unmapped_when_disabled(
    app: FastAPI,
    client: httpx.AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    router = ErrorAwareRouter(warn_on_unmapped=False)
    path = "/unmapped-quiet/"

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_409_CONFLICT,
        },
    )
    def unmapped() -> None:
        raise PlainError("x")

    app.include_router(router)

    with (
        caplog.at_level(logging.WARNING, logger="fastapi_error_map"),
        pytest.raises(PlainError),
    ):
        await client.get(path)

    assert caplog.records == []


async def test_more_specific_exception_type_wins(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/mro/"

    @router.get(
        path,
        error_map={
            ParentError: status.HTTP_400_BAD_REQUEST,
            ChildError: status.HTTP_409_CONFLICT,
        },
    )
    def mro() -> None:
        raise ChildError("child")

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_409_CONFLICT
    assert r.json() == {"error": "child"}


async def test_maps_exception_raised_in_dependency(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/dep/"

    def guard() -> None:
        raise ClientError("denied")

    @router.get(
        path,
        error_map={
            ClientError: status.HTTP_401_UNAUTHORIZED,
        },
        dependencies=[
            Depends(guard),
        ],
    )
    async def protected() -> None: ...

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    assert r.json() == {"error": "denied"}


async def test_awaits_async_def_on_error(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/async-on-error/"
    calls: list[str] = []

    async def record(_err: Exception) -> None:
        calls.append("async")

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

    assert calls == ["async"]


async def test_awaits_on_error_instance_with_async_call(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/async-callable-on-error/"
    calls: list[str] = []

    class AsyncHook:
        async def __call__(self, _err: Exception) -> None:
            calls.append("async-callable")

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_409_CONFLICT,
                on_error=AsyncHook(),
            ),
        },
    )
    async def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    await client.get(path)

    assert calls == ["async-callable"]


async def test_swallows_when_on_error_raises(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/on-error-raises/"

    def bad(_err: Exception) -> None:
        raise RuntimeError("side effect blew up")

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_409_CONFLICT,
                on_error=bad,
            ),
        },
    )
    async def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_409_CONFLICT
    assert r.json() == {"error": "x"}


async def test_propagates_base_exception_from_on_error(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/on-error-cancelled/"

    def cancel(_err: Exception) -> None:
        raise asyncio.CancelledError

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_409_CONFLICT,
                on_error=cancel,
            ),
        },
    )
    async def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    with pytest.raises(asyncio.CancelledError):
        await client.get(path)


async def test_propagates_when_translator_raises(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/translator-raises/"

    def bad(_err: Exception) -> dict[str, str]:
        raise ValueError("translator blew up")

    @router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_409_CONFLICT,
                translator=bad,
            ),
        },
    )
    async def boom() -> None:
        raise ClientError("x")

    app.include_router(router)

    with pytest.raises(ValueError, match="translator blew up"):
        await client.get(path)


async def test_broad_ancestor_does_not_hijack_request_validation(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter(warn_on_unmapped=False)
    path = "/catch-all/{item_id}/"

    @router.get(
        path,
        error_map={
            Exception: status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )
    def boom(item_id: int) -> None:
        _ = item_id
        raise ClientError("x")

    app.include_router(router)

    r = await client.get("/catch-all/not-an-int/")

    assert r.status_code == 422


async def test_broad_ancestor_does_not_hijack_http_exception(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    path = "/catch-all-http/"

    @router.get(
        path,
        error_map={
            Exception: status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )
    def boom() -> None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="gone",
        )

    app.include_router(router)

    r = await client.get(path)

    assert r.status_code == status.HTTP_404_NOT_FOUND
    assert r.json() == {"detail": "gone"}
