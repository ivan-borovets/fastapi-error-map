import asyncio
from typing import NoReturn
from unittest.mock import Mock

import pytest
from starlette.responses import JSONResponse

from fastapi_error_map import rule
from fastapi_error_map.error_handling import wrap_with_error_handling
from fastapi_error_map.translators import (
    DefaultClientErrorTranslator,
    DefaultServerErrorTranslator,
)
from tests.unit.error_stubs import ValidationError


def will_fail() -> NoReturn:
    raise ValidationError


@pytest.mark.asyncio
async def test_wrap_sync_passes_through() -> None:
    def add(a: int, b: int) -> int:
        return a + b

    sut = wrap_with_error_handling(
        func=add,
        error_map={},
        warn_on_unmapped=True,
        default_client_error_translator=DefaultClientErrorTranslator(),
        default_server_error_translator=DefaultServerErrorTranslator(),
        default_on_error=None,
    )

    result = await sut(2, 3)

    assert result == 5


@pytest.mark.asyncio
async def test_wrap_async_passes_through() -> None:
    async def async_add(x: int, y: int) -> int:
        await asyncio.sleep(0)
        return x + y

    sut = wrap_with_error_handling(
        func=async_add,
        error_map={},
        warn_on_unmapped=True,
        default_client_error_translator=DefaultClientErrorTranslator(),
        default_server_error_translator=DefaultServerErrorTranslator(),
        default_on_error=None,
    )

    result = await sut(3, 4)

    assert result == 7


@pytest.mark.asyncio
async def test_wrap_handles_mapped_error_and_returns_response() -> None:
    sut = wrap_with_error_handling(
        func=will_fail,
        error_map={ValidationError: 400},
        warn_on_unmapped=True,
        default_client_error_translator=DefaultClientErrorTranslator(),
        default_server_error_translator=DefaultServerErrorTranslator(),
        default_on_error=None,
    )

    result = await sut()

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400


@pytest.mark.asyncio
async def test_wrap_raises_runtime_error_on_unmapped_error_when_warn_true() -> None:
    sut = wrap_with_error_handling(
        func=will_fail,
        error_map={},
        warn_on_unmapped=True,
        default_client_error_translator=DefaultClientErrorTranslator(),
        default_server_error_translator=DefaultServerErrorTranslator(),
        default_on_error=None,
    )

    with pytest.raises(RuntimeError):
        await sut()


@pytest.mark.asyncio
async def test_wrap_raises_original_error_on_unmapped_error_when_warn_false() -> None:
    sut = wrap_with_error_handling(
        func=will_fail,
        error_map={},
        warn_on_unmapped=False,
        default_client_error_translator=DefaultClientErrorTranslator(),
        default_server_error_translator=DefaultServerErrorTranslator(),
        default_on_error=None,
    )

    with pytest.raises(ValidationError):
        await sut()


@pytest.mark.asyncio
async def test_wrap_calls_on_error_with_error_if_defined() -> None:
    mock_on_error = Mock()

    sut = wrap_with_error_handling(
        func=will_fail,
        error_map={
            ValidationError: rule(
                status=400,
                on_error=mock_on_error,
            )
        },
        warn_on_unmapped=True,
        default_client_error_translator=DefaultClientErrorTranslator(),
        default_server_error_translator=DefaultServerErrorTranslator(),
        default_on_error=None,
    )

    await sut()

    mock_on_error.assert_called_once()
    assert isinstance(mock_on_error.call_args[0][0], ValidationError)
