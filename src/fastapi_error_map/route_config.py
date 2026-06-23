from collections.abc import Callable
from typing import Any, Final, NoReturn

from fastapi.types import DecoratedCallable

from fastapi_error_map.rules import ErrorMap
from fastapi_error_map.types_ import OnError, RouteConfigError, TranslatorFactory

# RouteConfig channel: attached to the endpoint function (survives route re-creation).
ATTR: Final[str] = "__fastapi_error_map__"


class RouteConfig:
    def __init__(
        self,
        error_map: ErrorMap,
        translator_factory: TranslatorFactory | None = None,
        on_error: OnError | None = None,
        warn_on_unmapped: bool = True,
    ) -> None:
        self.error_map = error_map
        self.translator_factory = translator_factory
        self.on_error = on_error
        self.warn_on_unmapped = warn_on_unmapped

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RouteConfig):
            return NotImplemented
        return (
            dict(self.error_map) == dict(other.error_map)
            and self.translator_factory == other.translator_factory
            and self.on_error == other.on_error
            and self.warn_on_unmapped == other.warn_on_unmapped
        )

    def __hash__(self) -> NoReturn:
        raise TypeError(f"unhashable type: {type(self).__name__!r}")


def attach(func: Callable[..., Any], config: RouteConfig) -> None:
    existing: RouteConfig | None = getattr(func, ATTR, None)
    if existing is not None and existing != config:
        raise RouteConfigError(
            f"{func.__qualname__} already carries a different error_map"
        )
    setattr(func, ATTR, config)


def error_map(
    mapping: ErrorMap,
) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Carry ``error_map`` on endpoint — for routers other than ``ErrorAwareRouter``.

    Router must use ``route_class=ErrorAwareRoute``.
    With ``ErrorAwareRouter``, pass ``error_map=`` to route instead.

    Example:
        >>> router = APIRouter(route_class=ErrorAwareRoute)
        >>> @router.get("/accounts/{account_id}/")
        ... @error_map({ForbiddenError: 403})
        ... def get_account(account_id: int) -> Account: ...
    """

    def decorator(func: DecoratedCallable) -> DecoratedCallable:
        attach(func, RouteConfig(dict(mapping)))
        return func

    return decorator
