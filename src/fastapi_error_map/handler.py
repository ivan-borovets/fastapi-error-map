import logging

from fastapi.encoders import jsonable_encoder
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from fastapi_error_map.concurrency import run_on_error
from fastapi_error_map.framework import is_framework_exception
from fastapi_error_map.rules import CompiledErrorMap, ResolvedRule
from fastapi_error_map.types_ import RouteHandler, RouteLabel

logger = logging.getLogger("fastapi_error_map")
logger.addHandler(logging.NullHandler())


class _ErrorHandlingHandler:
    def __init__(
        self,
        original: RouteHandler,
        *,
        compiled: CompiledErrorMap,
        warn_on_unmapped: bool,
        route_label: RouteLabel,
    ) -> None:
        self.original = original
        self.compiled = compiled
        self.warn_on_unmapped = warn_on_unmapped
        self.route_label = route_label

    async def __call__(self, request: Request) -> Response:
        try:
            return await self.original(request)
        except Exception as err:
            if is_framework_exception(err):
                raise
            resolved = self._resolve(type(err))
            if resolved is None:
                self._log_unmapped(err)
                raise
            return await self._translate(resolved, err)

    def _resolve(self, exc_type: type[Exception]) -> ResolvedRule | None:
        ancestor: type[Exception]
        for ancestor in exc_type.__mro__:
            resolved = self.compiled.get(ancestor)
            if resolved is not None:
                return resolved
        return None

    def _log_unmapped(self, err: Exception) -> None:
        if self.warn_on_unmapped:
            logger.warning(
                "Unmapped %s on %s — add it to error_map or handle it globally",
                type(err).__name__,
                self.route_label,
            )

    async def _translate(self, resolved: ResolvedRule, err: Exception) -> Response:
        if resolved.on_error is not None:
            try:
                await run_on_error(resolved.on_error, err)
            except Exception:
                logger.warning(
                    "on_error failed on %s — response unaffected",
                    self.route_label,
                    exc_info=True,
                )
        logger.debug(
            "Translated %s -> %d on %s",
            type(err).__name__,
            resolved.status,
            self.route_label,
        )
        return JSONResponse(
            status_code=resolved.status,
            content=jsonable_encoder(resolved.translator(err)),
            headers=resolved.headers_for(err) or None,
        )


def wrap_route_handler(
    original: RouteHandler,
    *,
    compiled: CompiledErrorMap,
    warn_on_unmapped: bool,
    route_label: RouteLabel,
) -> RouteHandler:
    return _ErrorHandlingHandler(
        original,
        compiled=compiled,
        warn_on_unmapped=warn_on_unmapped,
        route_label=route_label,
    )
