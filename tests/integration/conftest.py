from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Callable

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

AsgiClientFactory = Callable[[FastAPI], AbstractAsyncContextManager[AsyncClient]]


@pytest.fixture
def app() -> FastAPI:
    return FastAPI()


@pytest.fixture
def asgi_client_factory() -> AsgiClientFactory:
    @asynccontextmanager
    async def _make(app: FastAPI) -> AsyncIterator[AsyncClient]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    return _make
