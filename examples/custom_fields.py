"""Your exceptions already carry the data — under different attribute names.

Point each ``structured()`` field at the attribute that holds it.
Every field is mapped explicitly — nothing is guessed.

Run: python -m examples.custom_fields
- POST /charges/0/ -> 402 {"code": "CARD_DECLINED", "message": "...", "details": {...}}
"""

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel
from starlette import status

from fastapi_error_map import ErrorAwareRouter, structured


class CardDeclinedError(Exception):
    def __init__(self) -> None:
        self.error_code = "CARD_DECLINED"
        self.reason = "card was declined"
        self.context: dict[str, Any] = {"retryable": False}


class Charge(BaseModel):
    charged: int


def make_app() -> FastAPI:
    factory = structured(
        code=lambda err: getattr(err, "error_code", None),
        message=lambda err: getattr(err, "reason", None),
        details=lambda err: getattr(err, "context", None),
    )
    router = ErrorAwareRouter(translator_factory=factory)

    @router.post(
        "/charges/{amount}/",
        error_map={
            CardDeclinedError: status.HTTP_402_PAYMENT_REQUIRED,
        },
    )
    def charge(amount: int) -> Charge:
        if amount == 0:
            raise CardDeclinedError
        return Charge(charged=amount)

    app = FastAPI()
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(make_app())
