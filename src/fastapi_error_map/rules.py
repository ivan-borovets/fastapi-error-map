import functools
import inspect
import typing
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Final, NamedTuple, TypeAlias, TypeVar

from fastapi_error_map.framework import (
    FRAMEWORK_EXCEPTIONS,
    is_framework_exception_type,
)
from fastapi_error_map.http_status import CLIENT_ERROR_FLOOR, ERROR_CEILING
from fastapi_error_map.translator_factories import simple
from fastapi_error_map.types_ import (
    ErrorMapWarning,
    Headers,
    OnError,
    RouteConfigError,
    RouteLabel,
    Translator,
    TranslatorFactory,
)

T = TypeVar("T")

# Owned by FastAPI request validation.
_HTTP_422_UNPROCESSABLE: Final[int] = 422


@dataclass(frozen=True, slots=True)
class Rule:
    """Full ``error_map`` entry; produced by ``rule()``."""

    status: int
    translator: Translator[Any] | None = None
    headers: Headers | None = None
    on_error: OnError | None = None
    openapi_model: type[Any] | None = None
    openapi_description: str | None = None
    openapi_examples: dict[str, Any] | None = None


ErrorMap: TypeAlias = Mapping[type[Exception], int | Rule]


def rule(
    status: int,
    *,
    translator: Translator[T] | None = None,
    headers: Headers | None = None,
    on_error: OnError | None = None,
    openapi_model: type[T] | None = None,
    openapi_description: str | None = None,
    openapi_examples: dict[str, Any] | None = None,
) -> Rule:
    """Extended ``error_map`` entry — when status alone is not enough.

    Adds ``translator``, ``headers``, ``on_error``, or OpenAPI
    ``openapi_description`` / ``openapi_examples``.
    Response model is read from translator's return annotation.
    Pass ``openapi_model`` when annotation is absent (lambda) or to override inference.

    ``headers``: static ``Mapping`` (shown in OpenAPI) or callable
    ``(err) -> Mapping[str, str]`` (per request, not introspected).
    Callable must return a mapping and must not raise — it shapes the response.
    Values reach the client verbatim on every status, 5xx included,
    so put only safe-to-expose data in headers.
    Set a custom ``Content-Type`` here too, e.g. ``application/problem+json``.

    Example:
        >>> error_map = {
        ...     UnauthorizedError: rule(
        ...         401,
        ...         headers={"WWW-Authenticate": "Bearer"},
        ...         on_error=log_unauthorized,
        ...     ),
        ... }
    """
    return Rule(
        status=status,
        translator=translator,
        headers=headers,
        on_error=on_error,
        openapi_model=openapi_model,
        openapi_description=openapi_description,
        openapi_examples=openapi_examples,
    )


@dataclass(frozen=True, slots=True)
class ResolvedRule:
    status: int
    translator: Translator[Any]
    static_headers: Mapping[str, str] | None
    dynamic_headers: Callable[[Exception], Mapping[str, str]] | None
    on_error: OnError | None
    openapi_model: type[Any]
    openapi_description: str | None
    openapi_examples: dict[str, Any] | None

    def headers_for(self, err: Exception) -> dict[str, str]:
        if self.dynamic_headers is not None:
            return dict(self.dynamic_headers(err))
        return dict(self.static_headers or {})


CompiledErrorMap: TypeAlias = Mapping[type[Exception], ResolvedRule]


def _is_error_status(status: int) -> bool:
    return CLIENT_ERROR_FLOOR <= status < ERROR_CEILING


def _annotation_target(translator: Translator[Any]) -> Any:
    if isinstance(translator, functools.partial):
        return translator.func
    if inspect.isfunction(translator) or inspect.ismethod(translator):
        return translator
    return type(translator).__call__


def _infer_model(translator: Translator[Any]) -> type[Any] | None:
    if isinstance(translator, type):  # e.g. translator=str — result is that type
        return translator
    try:
        hints = typing.get_type_hints(_annotation_target(translator))
    except (TypeError, NameError):
        return None
    ret = hints.get("return")
    # `-> None` means no model, not a null body — treat as missing annotation
    return None if ret is type(None) else ret


def _resolve_translator(
    rule_: Rule, translator_factory: TranslatorFactory | None
) -> Translator[Any]:
    if rule_.translator is not None:
        return rule_.translator
    factory = translator_factory or simple()
    return factory(rule_.status)


def _resolve_model(
    rule_: Rule,
    translator: Translator[Any],
    route_label: RouteLabel,
) -> type[Any]:
    if rule_.openapi_model is not None:
        return rule_.openapi_model
    inferred = _infer_model(translator)
    if inferred is None:
        raise RouteConfigError(
            f"{route_label}: translator has no return annotation — pass openapi_model=",
        )
    return inferred


class _SplitHeaders(NamedTuple):
    static: Mapping[str, str] | None
    dynamic: Callable[[Exception], Mapping[str, str]] | None


def _split_headers(headers: Headers | None) -> _SplitHeaders:
    if headers is None:
        return _SplitHeaders(static=None, dynamic=None)
    if isinstance(headers, Mapping):
        return _SplitHeaders(static=headers, dynamic=None)
    return _SplitHeaders(static=None, dynamic=headers)


# warn helpers fire from the router decorator; 3 reaches the user's route line
_DECORATOR_STACKLEVEL: Final[int] = 3
_FRAMEWORK_NAMES: Final[str] = " / ".join(t.__name__ for t in FRAMEWORK_EXCEPTIONS)


def warn_if_validation_shadowed(
    error_map: ErrorMap, *, route_label: RouteLabel
) -> None:
    for entry in error_map.values():
        status = entry.status if isinstance(entry, Rule) else entry
        if status == _HTTP_422_UNPROCESSABLE:
            warnings.warn(
                f"{route_label}: mapping 422 shadows FastAPI request validation",
                ErrorMapWarning,
                stacklevel=_DECORATOR_STACKLEVEL,
            )
            return


def warn_if_framework_exception_mapped(
    error_map: ErrorMap, *, route_label: RouteLabel
) -> None:
    for exc_type in error_map:
        if is_framework_exception_type(exc_type):
            warnings.warn(
                f"{route_label}: mapping {exc_type.__name__} has no effect — "
                f"{_FRAMEWORK_NAMES} are rendered by FastAPI, not error_map",
                ErrorMapWarning,
                stacklevel=_DECORATOR_STACKLEVEL,
            )


def compile_error_map(
    error_map: ErrorMap,
    *,
    translator_factory: TranslatorFactory | None,
    default_on_error: OnError | None,
    route_label: RouteLabel,
) -> dict[type[Exception], ResolvedRule]:
    compiled: dict[type[Exception], ResolvedRule] = {}
    for exc_type, entry in error_map.items():
        rule_ = entry if isinstance(entry, Rule) else Rule(status=entry)
        if not _is_error_status(rule_.status):
            raise RouteConfigError(
                f"{route_label}: status {rule_.status} is not 4xx/5xx"
            )
        translator = _resolve_translator(rule_, translator_factory)
        headers = _split_headers(rule_.headers)
        compiled[exc_type] = ResolvedRule(
            status=rule_.status,
            translator=translator,
            static_headers=headers.static,
            dynamic_headers=headers.dynamic,
            on_error=rule_.on_error or default_on_error,
            openapi_model=_resolve_model(rule_, translator, route_label),
            openapi_description=rule_.openapi_description,
            openapi_examples=rule_.openapi_examples,
        )
    return compiled
