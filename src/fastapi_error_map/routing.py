import inspect
from collections.abc import Callable
from typing import Any

from fastapi.routing import APIRoute, APIRouter
from fastapi.types import DecoratedCallable

from fastapi_error_map.handler import wrap_route_handler
from fastapi_error_map.openapi import build_openapi_responses
from fastapi_error_map.route_config import ATTR, RouteConfig, attach
from fastapi_error_map.rules import (
    ErrorMap,
    compile_error_map,
    warn_if_framework_exception_mapped,
    warn_if_validation_shadowed,
)
from fastapi_error_map.types_ import (
    OnError,
    RouteConfigError,
    RouteLabel,
    TranslatorFactory,
)


def _route_label(path: str, methods: Any = None) -> RouteLabel:
    return RouteLabel(f"{sorted(methods or [])} {path}")


class ErrorAwareRoute(APIRoute):
    """``APIRoute`` that applies the ``error_map`` from ``@error_map`` on the endpoint.

    Use as ``route_class=`` on a plain ``APIRouter`` instead of ``ErrorAwareRouter``.

    Example:
        >>> router = APIRouter(route_class=ErrorAwareRoute)
        >>> @router.get("/accounts/{account_id}/")
        ... @error_map({ForbiddenError: 403})
        ... def get_account(account_id: int) -> Account: ...
    """

    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        self._label = _route_label(path, kwargs.get("methods"))
        cfg: RouteConfig | None = getattr(endpoint, ATTR, None)
        if cfg is not None and cfg.error_map:
            self._compiled = compile_error_map(
                cfg.error_map,
                translator_factory=cfg.translator_factory,
                default_on_error=cfg.on_error,
                route_label=self._label,
            )
            kwargs["responses"] = build_openapi_responses(
                self._compiled, kwargs.get("responses")
            )
            self._warn_on_unmapped = cfg.warn_on_unmapped
        else:
            self._compiled = {}
            self._warn_on_unmapped = True
        super().__init__(path, endpoint, **kwargs)

    def get_route_handler(self) -> Callable[..., Any]:
        original = super().get_route_handler()
        if not self._compiled:
            return original
        return wrap_route_handler(
            original,
            compiled=self._compiled,
            warn_on_unmapped=self._warn_on_unmapped,
            route_label=self._label,
        )


class ErrorAwareRouter(APIRouter):
    """Drop-in ``APIRouter`` with per-route error mapping.

    Router-level ``translator_factory`` / ``on_error`` / ``warn_on_unmapped``
    set policy for every route; ``error_map`` per route adds to it.

    Example:
        >>> router = ErrorAwareRouter()
        >>> @router.get("/items/{item_id}/", error_map={ItemNotFoundError: 404})
        ... def get_item(item_id: int) -> Item: ...
    """

    def __init__(
        self,
        *,
        error_map: ErrorMap | None = None,
        translator_factory: TranslatorFactory | None = None,
        on_error: OnError | None = None,
        warn_on_unmapped: bool = True,
        **kwargs: Any,
    ) -> None:
        route_class = kwargs.setdefault("route_class", ErrorAwareRoute)
        if not issubclass(route_class, ErrorAwareRoute):
            raise RouteConfigError(
                f"route_class {route_class.__name__} must subclass ErrorAwareRoute — "
                f"error_map needs it to intercept; "
                f"drop route_class or subclass ErrorAwareRoute"
            )
        self._route_config = RouteConfig(
            dict(error_map or {}),
            translator_factory,
            on_error,
            warn_on_unmapped,
        )
        super().__init__(**kwargs)

    def api_route(
        self,
        path: str,
        *,
        error_map: ErrorMap | None = None,
        **kwargs: Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        merged: dict[type[Exception], Any] = {
            **self._route_config.error_map,
            **(error_map or {}),
        }
        parent = super().api_route(path, **kwargs)

        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            if merged:
                label = _route_label(path, kwargs.get("methods"))
                warn_if_framework_exception_mapped(merged, route_label=label)
                # param-less routes can't trigger validation; Depends may, so stay broad
                if inspect.signature(func).parameters:
                    warn_if_validation_shadowed(merged, route_label=label)
                attach(
                    func,
                    RouteConfig(
                        merged,
                        self._route_config.translator_factory,
                        self._route_config.on_error,
                        self._route_config.warn_on_unmapped,
                    ),
                )
            return parent(func)

        return decorator

    def get(
        self,
        path: str,
        *,
        error_map: ErrorMap | None = None,
        **kwargs: Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self.api_route(path, methods=["GET"], error_map=error_map, **kwargs)

    def put(
        self,
        path: str,
        *,
        error_map: ErrorMap | None = None,
        **kwargs: Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self.api_route(path, methods=["PUT"], error_map=error_map, **kwargs)

    def post(
        self,
        path: str,
        *,
        error_map: ErrorMap | None = None,
        **kwargs: Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self.api_route(path, methods=["POST"], error_map=error_map, **kwargs)

    def delete(
        self,
        path: str,
        *,
        error_map: ErrorMap | None = None,
        **kwargs: Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self.api_route(path, methods=["DELETE"], error_map=error_map, **kwargs)

    def options(
        self,
        path: str,
        *,
        error_map: ErrorMap | None = None,
        **kwargs: Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self.api_route(path, methods=["OPTIONS"], error_map=error_map, **kwargs)

    def head(
        self,
        path: str,
        *,
        error_map: ErrorMap | None = None,
        **kwargs: Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self.api_route(path, methods=["HEAD"], error_map=error_map, **kwargs)

    def patch(
        self,
        path: str,
        *,
        error_map: ErrorMap | None = None,
        **kwargs: Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self.api_route(path, methods=["PATCH"], error_map=error_map, **kwargs)

    def trace(
        self,
        path: str,
        *,
        error_map: ErrorMap | None = None,
        **kwargs: Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self.api_route(path, methods=["TRACE"], error_map=error_map, **kwargs)

    def websocket(
        self,
        path: str,
        name: str | None = None,
        *,
        error_map: ErrorMap | None = None,
        **kwargs: Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        if error_map is not None:
            raise RouteConfigError(
                f"{path}: error_map is not supported on WebSocket routes — "
                f"error mapping wraps HTTP only"
            )
        return super().websocket(path, name, **kwargs)
