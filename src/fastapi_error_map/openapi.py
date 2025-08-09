from typing import Any, Union

from fastapi_error_map.rules import ErrorMap
from fastapi_error_map.translator_policy import pick_translator_for_status
from fastapi_error_map.translators import ErrorTranslator


def build_openapi_responses(
    *,
    error_map: ErrorMap,
    default_client_error_translator: ErrorTranslator[Any],
    default_server_error_translator: ErrorTranslator[Any],
) -> dict[Union[int, str], dict[str, Any]]:
    responses: dict[Union[int, str], dict[str, Any]] = {}

    for value in error_map.values():
        if isinstance(value, int):
            status = value
            translator = None
        else:
            status = value.status
            translator = value.translator

        if translator is None:
            translator = pick_translator_for_status(
                status=status,
                default_client_error_translator=default_client_error_translator,
                default_server_error_translator=default_server_error_translator,
            )

        response_model = translator.error_response_model_cls
        responses[status] = {"model": response_model}

    return responses
