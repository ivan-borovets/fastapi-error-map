import asyncio
from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport

from fastapi_error_map import ErrorAwareRouter, rule


class CustomError(Exception):
    pass


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
async def test_error_aware_router_routes(method: str) -> None:
    app = FastAPI()
    router = ErrorAwareRouter()
    router_path = "/fail"
    error_message = "This is a test"
    error_status_code = 418
    mock_on_error = Mock()

    async def failing_endpoint() -> None:
        await asyncio.sleep(0)
        raise CustomError(error_message)

    getattr(router, method)(
        router_path,
        error_map={
            CustomError: rule(status=error_status_code, on_error=mock_on_error),
        },
    )(failing_endpoint)
    app.include_router(router)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response: httpx.Response = await getattr(client, method)(router_path)
        openapi_response: httpx.Response = await client.get("/openapi.json")

    response_data = response.json()
    assert response.status_code == error_status_code
    assert response.headers["content-type"].startswith("application/json")
    assert response_data == {"error": error_message}
    mock_on_error.assert_called_once()
    assert isinstance(mock_on_error.call_args[0][0], CustomError)
    assert str(mock_on_error.call_args[0][0]) == error_message

    openapi_data = openapi_response.json()
    path_item = openapi_data["paths"][router_path][method]
    documented_responses = path_item["responses"]
    assert str(error_status_code) in documented_responses
