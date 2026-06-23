# FastAPI's own exceptions (validation -> 422, HTTPException). error_map never touches
# them, so a broad mapping like {Exception: 500} can't turn a 422/404 into 500.
from typing import Final

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

FRAMEWORK_EXCEPTIONS: Final[tuple[type[Exception], ...]] = (
    HTTPException,
    RequestValidationError,
)


def is_framework_exception(err: Exception) -> bool:
    return isinstance(err, FRAMEWORK_EXCEPTIONS)


def is_framework_exception_type(exc_type: type[Exception]) -> bool:
    return issubclass(exc_type, FRAMEWORK_EXCEPTIONS)
