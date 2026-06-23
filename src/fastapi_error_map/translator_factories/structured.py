from collections.abc import Callable, Mapping
from typing import Any

from typing_extensions import NotRequired, TypedDict

from fastapi_error_map.http_status import SERVER_ERROR_FLOOR, status_name
from fastapi_error_map.translator_factories.common import DEFAULT_SERVER_MESSAGE
from fastapi_error_map.types_ import TranslatorFactory


class StructuredErrorResponse(TypedDict):
    """Response body produced by ``structured()``."""

    code: str
    message: NotRequired[str]
    details: NotRequired[dict[str, Any]]


def default_code(err: Exception) -> str | None:
    code = getattr(err, "code", None)
    return code if isinstance(code, str) and code else None


def default_message(err: Exception) -> str | None:
    return str(err) or None


def default_details(err: Exception) -> Mapping[str, Any] | None:
    details = getattr(err, "details", None)
    return details if isinstance(details, Mapping) else None


# Two-phase factory, same shape as simple.py.
# _Structured(status) returns _StructuredFor, which renders body per request.
# _Structured also holds extractors and config captured once in structured().


class _StructuredFor:
    def __init__(
        self,
        render: Callable[[Exception, int], StructuredErrorResponse],
        status: int,
    ) -> None:
        self.render = render
        self.status = status

    def __call__(self, err: Exception) -> StructuredErrorResponse:
        return self.render(err, self.status)


class _Structured:
    def __init__(
        self,
        code: Callable[[Exception], str | None],
        message: Callable[[Exception], str | None],
        details: Callable[[Exception], Mapping[str, Any] | None],
        exposed_5xx_types: tuple[type[Exception], ...],
        server_message: str,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        self.exposed_5xx_types = exposed_5xx_types
        self.server_message = server_message

    def __call__(self, status: int) -> _StructuredFor:
        return _StructuredFor(self._render, status)

    def _render(self, err: Exception, status: int) -> StructuredErrorResponse:
        if status >= SERVER_ERROR_FLOOR and not isinstance(err, self.exposed_5xx_types):
            return StructuredErrorResponse(
                code=status_name(status),
                message=self.server_message,
            )
        code = self.code(err)
        message = self.message(err)
        details = self.details(err)
        body = StructuredErrorResponse(
            code=code if isinstance(code, str) and code else status_name(status),
        )
        if isinstance(message, str) and message:
            body["message"] = message
        if isinstance(details, Mapping):
            body["details"] = dict(details)
        return body


def structured(
    *,
    code: Callable[[Exception], str | None] = default_code,
    message: Callable[[Exception], str | None] = default_message,
    details: Callable[[Exception], Mapping[str, Any] | None] = default_details,
    exposed_5xx_types: tuple[type[Exception], ...] = (),
    server_message: str = DEFAULT_SERVER_MESSAGE,
) -> TranslatorFactory:
    """``{code, message, details}`` envelope.

    Defaults read ``err.code`` / ``str(err)`` / ``err.details``.
    Missing ``code`` falls back to status name (e.g. ``"HTTP_404_NOT_FOUND"``).
    Absent ``message`` / ``details``: key omitted, never ``null``
    (empty mapping stays ``{}``).
    Need explicit nulls: write own factory.

    5xx opaque — ``message`` is ``server_message``, never ``str(err)``;
    ``exposed_5xx_types`` whitelists types to render in full.
    Opacity is body-only; ``rule(headers=...)`` values are not redacted.

    Attributes under other names: map each field explicitly.
    Different envelope entirely: write own factory.

    Example:
        >>> factory = structured(
        ...     code=lambda err: err.error_code,
        ...     message=lambda err: err.reason,
        ...     details=lambda err: err.context,
        ... )
        >>> router = ErrorAwareRouter(translator_factory=factory)
    """
    return _Structured(code, message, details, exposed_5xx_types, server_message)
