from collections.abc import Awaitable, Callable, Mapping
from typing import Any, NewType, TypeAlias, TypeVar

from starlette.requests import Request
from starlette.responses import Response

T = TypeVar("T")

# Format: "['GET'] /users/{id}".
RouteLabel = NewType("RouteLabel", str)

Translator: TypeAlias = Callable[[Exception], T]
OnError: TypeAlias = Callable[[Exception], Awaitable[None] | None]
Headers: TypeAlias = Mapping[str, str] | Callable[[Exception], Mapping[str, str]]
TranslatorFactory: TypeAlias = Callable[[int], Translator[Any]]
RouteHandler: TypeAlias = Callable[[Request], Awaitable[Response]]
OpenApiResponses: TypeAlias = dict[int | str, dict[str, Any]]


class ErrorMapWarning(UserWarning):
    """Suspicious but runnable ``error_map`` entry."""


class RouteConfigError(Exception):
    """Invalid route config; fatal at build."""
