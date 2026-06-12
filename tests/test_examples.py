from collections.abc import AsyncIterator

import httpx
import pytest
from starlette import status

from examples import (
    custom_factory,
    custom_fields,
    extended_rule,
    interop,
    quickstart,
    readme_quickstart,
    structured_envelope,
)


@pytest.fixture
async def client(request: pytest.FixtureRequest) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=request.param()),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.parametrize("client", [quickstart.make_app], indirect=True)
async def test_quickstart_maps_exception_to_status(client: httpx.AsyncClient) -> None:
    r = await client.get("/items/0/")

    assert r.status_code == status.HTTP_404_NOT_FOUND
    assert r.json() == {"error": "item 0 not found"}


@pytest.mark.parametrize("client", [readme_quickstart.make_app], indirect=True)
async def test_readme_quickstart_maps_short_form(client: httpx.AsyncClient) -> None:
    r = await client.get("/stock/")

    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    assert r.json() == {"error": "authorization required"}


@pytest.mark.parametrize("client", [readme_quickstart.make_app], indirect=True)
async def test_readme_quickstart_maps_full_form_rule(client: httpx.AsyncClient) -> None:
    r = await client.get("/stock/", params={"user_id": 1})

    assert r.status_code == status.HTTP_409_CONFLICT
    assert r.json() == {"error": "no items available"}


@pytest.mark.parametrize("client", [structured_envelope.make_app], indirect=True)
async def test_structured_envelope_fills_code_message_details(
    client: httpx.AsyncClient,
) -> None:
    r = await client.get("/orders/1/")

    assert r.json() == {
        "code": "ALREADY_PAID",
        "message": "order already paid",
        "details": {"order_id": 1},
    }


@pytest.mark.parametrize("client", [structured_envelope.make_app], indirect=True)
async def test_structured_envelope_keeps_5xx_opaque(client: httpx.AsyncClient) -> None:
    r = await client.get("/orders/0/")

    assert r.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert r.json()["message"] == "Internal server error"
    assert "10.0.0.5" not in r.text


@pytest.mark.parametrize("client", [extended_rule.make_app], indirect=True)
async def test_extended_rule_applies_body_and_header(client: httpx.AsyncClient) -> None:
    r = await client.get("/reports/0/")

    assert r.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert r.json() == {"reason": "rate limit exceeded"}
    assert r.headers["Retry-After"] == "30"


@pytest.mark.parametrize("client", [custom_factory.make_app], indirect=True)
async def test_custom_factory_renders_problem_details(
    client: httpx.AsyncClient,
) -> None:
    r = await client.get("/accounts/0/")

    assert r.status_code == status.HTTP_403_FORBIDDEN
    assert r.headers["content-type"] == "application/problem+json"
    assert r.json() == {
        "type": "about:blank",
        "title": "Forbidden",
        "status": status.HTTP_403_FORBIDDEN,
        "detail": "you do not own this account",
    }


@pytest.mark.parametrize("client", [custom_fields.make_app], indirect=True)
async def test_custom_fields_reads_renamed_attributes(
    client: httpx.AsyncClient,
) -> None:
    r = await client.post("/charges/0/")

    assert r.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert r.json() == {
        "code": "CARD_DECLINED",
        "message": "card was declined",
        "details": {"retryable": False},
    }


@pytest.mark.parametrize("client", [interop.make_app], indirect=True)
async def test_interop_maps_via_route_class_and_decorator(
    client: httpx.AsyncClient,
) -> None:
    r = await client.get("/accounts/0/")

    assert r.status_code == status.HTTP_403_FORBIDDEN
    assert r.json() == {"error": "you do not own this account"}


@pytest.mark.parametrize(
    ("client", "expected_status"),
    [
        (quickstart.make_app, status.HTTP_404_NOT_FOUND),
        (readme_quickstart.make_app, status.HTTP_401_UNAUTHORIZED),
        (structured_envelope.make_app, status.HTTP_409_CONFLICT),
        (structured_envelope.make_app, status.HTTP_503_SERVICE_UNAVAILABLE),
        (custom_fields.make_app, status.HTTP_402_PAYMENT_REQUIRED),
        (extended_rule.make_app, status.HTTP_429_TOO_MANY_REQUESTS),
        (custom_factory.make_app, status.HTTP_403_FORBIDDEN),
        (interop.make_app, status.HTTP_403_FORBIDDEN),
    ],
    indirect=["client"],
)
async def test_example_documents_error_in_openapi(
    client: httpx.AsyncClient,
    expected_status: int,
) -> None:
    response = await client.get("/openapi.json")
    schema = response.json()

    documented = {
        code
        for path in schema["paths"].values()
        for method in path.values()
        for code in method["responses"]
    }
    assert str(expected_status) in documented
