"""One error needs more than a status: a header, a side effect, a documented body.

``rule()`` carries all of it in the same declaration — here a 429 with a
``Retry-After`` header, an alert callback, and an OpenAPI description.

Run: python -m examples.extended_rule
- GET /reports/0/ -> 429 {"reason": "..."} with a Retry-After header
"""

import logging

from fastapi import FastAPI
from pydantic import BaseModel
from starlette import status
from typing_extensions import TypedDict

from fastapi_error_map import ErrorAwareRouter, rule

logger = logging.getLogger("examples")


class RateLimitedError(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("rate limit exceeded")
        self.retry_after = retry_after


class Report(BaseModel):
    report_id: int


class TooManyRequestsBody(TypedDict):
    reason: str


def to_body(err: Exception) -> TooManyRequestsBody:
    return TooManyRequestsBody(reason=str(err))


def retry_after_header(err: Exception) -> dict[str, str]:
    return {"Retry-After": str(getattr(err, "retry_after", 60))}


def log_rate_limit(err: Exception) -> None:
    logger.warning("rate limit hit: %s", err)


def make_app() -> FastAPI:
    router = ErrorAwareRouter()

    @router.get(
        "/reports/{report_id}/",
        error_map={
            RateLimitedError: rule(
                status.HTTP_429_TOO_MANY_REQUESTS,
                translator=to_body,
                headers=retry_after_header,
                on_error=log_rate_limit,
                openapi_description="Per-client report quota exhausted.",
            ),
        },
    )
    def get_report(report_id: int) -> Report:
        if report_id == 0:
            raise RateLimitedError(retry_after=30)
        return Report(report_id=report_id)

    app = FastAPI()
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(make_app())
