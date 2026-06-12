"""The README Quickstart, runnable end to end.

One route maps two exceptions to two statuses.
Short form maps a status; ``rule()`` adds a side effect.
The default translator renders both as ``{"error": ...}``.

Run: python -m examples.readme_quickstart
- GET /stock/           -> 401 {"error": "authorization required"}
- GET /stock/?user_id=1 -> 409 {"error": "no items available"}
"""

from fastapi import FastAPI
from pydantic import BaseModel

from fastapi_error_map import ErrorAwareRouter, rule


class AuthorizationError(Exception): ...


class OutOfStockError(Exception): ...


class Stock(BaseModel):
    available: int


def notify(err: Exception) -> None:
    print(f"out of stock: {err}")


def make_app() -> FastAPI:
    router = ErrorAwareRouter()

    @router.get(
        "/stock/",
        error_map={
            AuthorizationError: 401,
            OutOfStockError: rule(409, on_error=notify),
        },
    )
    def check_stock(user_id: int = 0) -> Stock:
        if user_id == 0:
            raise AuthorizationError("authorization required")
        raise OutOfStockError("no items available")

    app = FastAPI()
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(make_app())
