"""Keep a consistent error envelope, and never leak 5xx internals to the client.

``structured()`` reads ``err.code`` / ``str(err)`` / ``err.details`` into a
``{code, message, details}`` body.
5xx stays opaque by default — the upstream detail is logged, not returned.

Run: python -m examples.structured_envelope
- GET /orders/1/ -> 409 {"code": "ALREADY_PAID", "message": "...", "details": {...}}
- GET /orders/0/ -> 503 {"code": "HTTP_503_...", "message": "Internal server error"}
"""

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel
from starlette import status

from fastapi_error_map import ErrorAwareRouter, structured


class AlreadyPaidError(Exception):
    def __init__(self, order_id: int) -> None:
        super().__init__("order already paid")
        self.code = "ALREADY_PAID"
        self.details: dict[str, Any] = {"order_id": order_id}


class UpstreamDownError(Exception): ...


class Order(BaseModel):
    order_id: int


def make_app() -> FastAPI:
    router = ErrorAwareRouter(translator_factory=structured())

    @router.get(
        "/orders/{order_id}/",
        error_map={
            AlreadyPaidError: status.HTTP_409_CONFLICT,
            UpstreamDownError: status.HTTP_503_SERVICE_UNAVAILABLE,
        },
    )
    def pay_order(order_id: int) -> Order:
        if order_id == 0:
            raise UpstreamDownError("payment gateway timeout at 10.0.0.5")
        raise AlreadyPaidError(order_id)

    app = FastAPI()
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(make_app())
