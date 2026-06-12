import pytest
from starlette import status

from fastapi_error_map import (
    ErrorAwareRouter,
    RouteConfigError,
    rule,
)
from tests.factories import ClientError


def test_fails_when_translator_has_no_return_annotation() -> None:
    router = ErrorAwareRouter()
    path = "/no-annotation/"

    def translate(err):  # type: ignore[no-untyped-def]
        return {"reason": str(err)}

    declare = router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_418_IM_A_TEAPOT,
                translator=translate,
            ),
        },
    )

    def boom() -> None:
        raise ClientError("x")

    with pytest.raises(RouteConfigError, match=path):
        declare(boom)


def test_fails_when_translator_has_none_return_annotation() -> None:
    router = ErrorAwareRouter()
    path = "/annotated-none/"

    def translate(_err: Exception) -> None: ...

    declare = router.get(
        path,
        error_map={
            ClientError: rule(
                status.HTTP_418_IM_A_TEAPOT,
                translator=translate,
            ),
        },
    )

    def boom() -> None:
        raise ClientError("x")

    with pytest.raises(RouteConfigError, match=path):
        declare(boom)


def test_fails_for_non_error_status() -> None:
    router = ErrorAwareRouter()

    declare = router.get(
        "/bad-status/",
        error_map={
            ClientError: status.HTTP_200_OK,
        },
    )

    def boom() -> None:
        raise ClientError("x")

    with pytest.raises(RouteConfigError):
        declare(boom)
