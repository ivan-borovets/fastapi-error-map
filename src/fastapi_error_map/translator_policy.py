from typing import Any

from fastapi_error_map.translators import ErrorTranslator


def is_server_error(status: int) -> bool:
    return status // 100 == 5


def is_client_error(status: int) -> bool:
    return status // 100 == 4


def validate_error_status(status: int) -> None:
    if not (is_client_error(status) or is_server_error(status)):
        raise RuntimeError(f"Unsupported status for error_map: {status}. Use 4xx/5xx.")


def pick_translator_for_status(
    *,
    status: int,
    default_client_error_translator: ErrorTranslator[Any],
    default_server_error_translator: ErrorTranslator[Any],
) -> ErrorTranslator[Any]:
    return (
        default_server_error_translator
        if is_server_error(status)
        else default_client_error_translator
    )
