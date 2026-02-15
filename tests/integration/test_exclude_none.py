import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx
import pytest
from fastapi import FastAPI

from fastapi_error_map import ErrorAwareRouter, rule
from fastapi_error_map.translators import ErrorTranslator


class CustomError(Exception):
    pass


@dataclass
class ClientErrorWithOptionalDetails:
    error: str
    details: Optional[str] = None


class OptionalDetailsTranslator(ErrorTranslator[ClientErrorWithOptionalDetails]):
    @property
    def error_response_model_cls(self) -> type[ClientErrorWithOptionalDetails]:
        return ClientErrorWithOptionalDetails

    def from_error(self, err: Exception) -> ClientErrorWithOptionalDetails:
        return ClientErrorWithOptionalDetails(error=str(err), details=None)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
async def test_exclude_none_false_keeps_null_fields(
    method: str,
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    translator = OptionalDetailsTranslator()

    async def failing_endpoint() -> None:
        await asyncio.sleep(0)
        raise CustomError("boom")

    getattr(router, method)(
        "/fail",
        error_map={CustomError: rule(status=418, translator=translator)},
        exclude_none=False,
    )(failing_endpoint)
    app.include_router(router)

    response: httpx.Response = await getattr(client, method)("/fail")

    assert response.status_code == 418
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"error": "boom", "details": None}


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
async def test_exclude_none_true_drops_null_fields(
    method: str,
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    router = ErrorAwareRouter()
    translator = OptionalDetailsTranslator()

    async def failing_endpoint() -> None:
        await asyncio.sleep(0)
        raise CustomError("boom")

    getattr(router, method)(
        "/fail",
        error_map={CustomError: rule(status=418, translator=translator)},
        exclude_none=True,
    )(failing_endpoint)
    app.include_router(router)

    response: httpx.Response = await getattr(client, method)("/fail")

    assert response.status_code == 418
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"error": "boom"}
