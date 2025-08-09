from typing import Any

from starlette import status as http_status

from fastapi_error_map.translators import ErrorTranslator


def is_server_error(status: int) -> bool:
    return status >= http_status.HTTP_500_INTERNAL_SERVER_ERROR


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
