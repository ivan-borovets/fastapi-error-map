import functools
import inspect
from dataclasses import dataclass

from starlette.concurrency import run_in_threadpool

from fastapi_error_map.types_ import OnError, RouteConfigError


def _is_async_callable(on_error: OnError) -> bool:
    while isinstance(on_error, functools.partial):
        on_error = on_error.func
    if inspect.iscoroutinefunction(on_error):
        return True
    # callable instance: async-ness lives on __call__, not the instance
    call = getattr(type(on_error), "__call__", None)  # noqa: B004
    return inspect.iscoroutinefunction(call)


@dataclass(frozen=True, slots=True)
class _Offloaded:
    wrapped: OnError

    def __call__(self, err: Exception) -> None:  # noqa: ARG002
        raise TypeError("_Offloaded is a marker, not callable")


def to_threadpool(on_error: OnError) -> OnError:
    """Mark a blocking sync ``on_error`` to run in a threadpool, off the loop.

    For a sync callback that blocks (sync HTTP, disk): keeps it from stalling
    the loop for other requests. The response still awaits it, so latency is
    unchanged — to answer without waiting, schedule the work instead.
    Sync runs inline by default; async runs inline always, offloading one raises.

    Example:
        >>> rule(503, on_error=to_threadpool(write_audit_log))
    """
    if isinstance(on_error, _Offloaded):
        raise RouteConfigError("to_threadpool applied twice to the same on_error")
    if _is_async_callable(on_error):
        raise RouteConfigError("cannot offload an async on_error — it runs inline")
    return _Offloaded(on_error)


async def run_on_error(on_error: OnError, err: Exception) -> None:
    if isinstance(on_error, _Offloaded):
        await run_in_threadpool(on_error.wrapped, err)
    elif _is_async_callable(on_error):
        result = on_error(err)
        if inspect.isawaitable(result):
            await result
    else:
        on_error(err)
