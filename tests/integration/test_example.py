from typing import TYPE_CHECKING

import pytest

from examples.main import create_app
from tests.integration.conftest import AsgiClientFactory

if TYPE_CHECKING:
    import httpx


@pytest.mark.asyncio
async def test_check_stock(
    asgi_client_factory: AsgiClientFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = create_app()

    async with asgi_client_factory(app) as client:
        authz_err_response: httpx.Response = await client.get("/stock?user_id=0")
        out_of_stock_err_response: httpx.Response = await client.get("/stock?user_id=1")
        openapi_response: httpx.Response = await client.get("/openapi.json")

    assert authz_err_response.status_code == 401
    assert authz_err_response.headers["content-type"].startswith("application/json")
    authz_err_response_data = authz_err_response.json()
    assert authz_err_response_data == {"error": ""}

    assert out_of_stock_err_response.status_code == 409
    assert out_of_stock_err_response.headers["content-type"].startswith(
        "application/json"
    )
    out_of_stock_err_response_data = out_of_stock_err_response.json()
    assert out_of_stock_err_response_data == {"error": "No items available."}

    openapi_response_data = openapi_response.json()
    path_item = openapi_response_data["paths"]["/stock"]["get"]
    documented_responses = path_item["responses"]
    assert str(401) in documented_responses
    assert str(409) in documented_responses

    captured = capsys.readouterr()
    assert "Notified admin: No items available.\n" in captured.out
