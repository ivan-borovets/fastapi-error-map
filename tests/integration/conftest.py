from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI


@pytest.fixture
def app() -> FastAPI:
    return FastAPI()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
