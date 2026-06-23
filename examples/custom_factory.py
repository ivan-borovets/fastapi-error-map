"""You need a whole different envelope — not ``{code, message, details}``.

Write your own factory: ``(status) -> (err) -> body``.
``simple()`` and ``structured()`` are built the same way.
Body is RFC 9457 problem details (all members optional; ``instance`` omitted here).
``rule(headers=)`` sets the ``application/problem+json`` content type.

Run: python -m examples.custom_factory
- GET /accounts/0/ -> 403 application/problem+json
  {"type": "about:blank", "title": "Forbidden", "status": 403, "detail": "..."}
"""

from collections.abc import Callable
from http import HTTPStatus
from typing import Final

from fastapi import FastAPI
from pydantic import BaseModel
from starlette import status
from typing_extensions import TypedDict

from fastapi_error_map import ErrorAwareRouter, rule

PROBLEM_JSON: Final[str] = "application/problem+json"


class ProblemDetail(TypedDict):
    type: str
    title: str
    status: int
    detail: str


def problem_detail(status_code: int) -> Callable[[Exception], ProblemDetail]:
    title = HTTPStatus(status_code).phrase

    def translate(err: Exception) -> ProblemDetail:
        return ProblemDetail(
            type="about:blank",
            title=title,
            status=status_code,
            detail=str(err),
        )

    return translate


class ForbiddenError(Exception): ...


class Account(BaseModel):
    account_id: int


def make_app() -> FastAPI:
    router = ErrorAwareRouter(translator_factory=problem_detail)

    @router.get(
        "/accounts/{account_id}/",
        error_map={
            ForbiddenError: rule(
                status.HTTP_403_FORBIDDEN,
                headers={"Content-Type": PROBLEM_JSON},
            ),
        },
    )
    def get_account(account_id: int) -> Account:
        if account_id == 0:
            raise ForbiddenError("you do not own this account")
        return Account(account_id=account_id)

    app = FastAPI()
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(make_app())
