"""Per-endpoint error handling for FastAPI that keeps OpenAPI in sync.

Declare on the route how exceptions map to HTTP responses;
OpenAPI error docs follow from that declaration.
"""

from fastapi_error_map.concurrency import to_threadpool
from fastapi_error_map.route_config import error_map
from fastapi_error_map.routing import ErrorAwareRoute, ErrorAwareRouter
from fastapi_error_map.rules import ErrorMap, Rule, rule
from fastapi_error_map.translator_factories import (
    SimpleErrorResponse,
    StructuredErrorResponse,
    simple,
    structured,
)
from fastapi_error_map.types_ import (
    ErrorMapWarning,
    Headers,
    OnError,
    RouteConfigError,
    Translator,
    TranslatorFactory,
)

__all__ = [
    "ErrorAwareRoute",
    "ErrorAwareRouter",
    "ErrorMap",
    "ErrorMapWarning",
    "Headers",
    "OnError",
    "RouteConfigError",
    "Rule",
    "SimpleErrorResponse",
    "StructuredErrorResponse",
    "Translator",
    "TranslatorFactory",
    "error_map",
    "rule",
    "simple",
    "structured",
    "to_threadpool",
]
