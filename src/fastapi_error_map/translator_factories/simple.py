from typing_extensions import TypedDict

from fastapi_error_map.http_status import SERVER_ERROR_FLOOR
from fastapi_error_map.translator_factories.common import DEFAULT_SERVER_MESSAGE
from fastapi_error_map.types_ import TranslatorFactory


class SimpleErrorResponse(TypedDict):
    """Response body produced by ``simple()``."""

    error: str


# TranslatorFactory runs in two phases.
# Phase 1 is factory(status), once per route at compile time (rules.py).
# Phase 2 is translator(err), once per request on raised error (handler.py).
# So _Simple(status) returns _SimpleFor, which renders each request to its route.


class _SimpleFor:
    def __init__(self, status: int) -> None:
        self.status = status

    def __call__(self, err: Exception) -> SimpleErrorResponse:
        if self.status >= SERVER_ERROR_FLOOR:
            return SimpleErrorResponse(error=DEFAULT_SERVER_MESSAGE)
        return SimpleErrorResponse(error=str(err))


class _Simple:
    def __call__(self, status: int) -> _SimpleFor:
        return _SimpleFor(status)


def simple() -> TranslatorFactory:
    """``{"error": str(err)}`` for 4xx, opaque message for 5xx.

    Default factory.
    Reads only ``str(err)`` — works on any exception.
    Opacity is body-only; ``rule(headers=...)`` values are sent as-is.
    Rarely written explicitly:
        >>> router = ErrorAwareRouter(translator_factory=simple())
    """
    return _Simple()
