import inspect
from collections.abc import Awaitable
from functools import wraps
from typing import Any, Callable, Optional, Union

from fastapi.encoders import jsonable_encoder
from fastapi.responses import ORJSONResponse
from starlette.concurrency import run_in_threadpool

from fastapi_error_map.rules import ErrorMap, resolve_rule_for_error
from fastapi_error_map.translators import ErrorTranslator


def wrap_with_error_handling(
    *,
    func: Callable[..., Any],
    error_map: ErrorMap,
    warn_on_unmapped: bool,
    default_client_error_translator: ErrorTranslator[Any],
    default_server_error_translator: ErrorTranslator[Any],
    default_on_error: Optional[Callable[[Exception], Union[Awaitable[None], None]]],
) -> Callable[..., Any]:
    is_coro = inspect.iscoroutinefunction(func)

    @wraps(func)
    async def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            if is_coro:
                return await func(*args, **kwargs)
            return await run_in_threadpool(func, *args, **kwargs)
        except Exception as error:
            return await handle_with_error_map(
                error=error,
                error_map=error_map,
                warn_on_unmapped=warn_on_unmapped,
                default_client_error_translator=default_client_error_translator,
                default_server_error_translator=default_server_error_translator,
                default_on_error=default_on_error,
            )

    return wrapped


async def handle_with_error_map(
    *,
    error: Exception,
    error_map: ErrorMap,
    warn_on_unmapped: bool,
    default_client_error_translator: ErrorTranslator[Any],
    default_server_error_translator: ErrorTranslator[Any],
    default_on_error: Optional[Callable[[Exception], Union[Awaitable[None], None]]],
) -> ORJSONResponse:
    try:
        rule = resolve_rule_for_error(
            error=error,
            error_map=error_map,
            default_client_error_translator=default_client_error_translator,
            default_server_error_translator=default_server_error_translator,
            default_on_error=default_on_error,
        )
    except RuntimeError as exc:
        if warn_on_unmapped:
            raise
        original = exc.__cause__ or exc
        raise original.with_traceback(original.__traceback__) from None

    if rule.on_error is not None:
        if inspect.iscoroutinefunction(rule.on_error):
            await rule.on_error(error)
        else:
            result = await run_in_threadpool(rule.on_error, error)
            if inspect.isawaitable(result):
                await result

    content = rule.translator.from_error(error)
    return ORJSONResponse(
        status_code=rule.status,
        content=jsonable_encoder(content),
    )
