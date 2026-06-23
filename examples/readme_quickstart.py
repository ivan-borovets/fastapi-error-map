"""The README Quickstart, runnable end to end.

One route maps two exceptions to two statuses.
Short form maps a status; ``rule()`` adds a side effect.
The default translator renders both as ``{"error": ...}``.

Run: python -m examples.readme_quickstart
- GET /stock/           -> 401 {"error": "authentication required"}
- GET /stock/?user_id=1 -> 404 {"error": "user 1 not found"}
"""

from fastapi import FastAPI
from pydantic import BaseModel

from fastapi_error_map import ErrorAwareRouter, rule


class AuthenticationError(Exception): ...


class UserNotFoundError(Exception): ...


class Stock(BaseModel):
    available: int


def notify(err: Exception) -> None:
    print(f"lookup failed: {err}")


def make_app() -> FastAPI:
    router = ErrorAwareRouter()

    @router.get(
        "/stock/",
        error_map={
            AuthenticationError: 401,
            UserNotFoundError: rule(404, on_error=notify),
        },
    )
    def check_stock(user_id: int = 0) -> Stock:
        if user_id == 0:
            raise AuthenticationError("authentication required")
        raise UserNotFoundError(f"user {user_id} not found")

    app = FastAPI()
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(make_app())
