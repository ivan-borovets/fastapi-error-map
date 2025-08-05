from typing import Any, Union

from fastapi_error_map.rules import ErrorMap
from fastapi_error_map.translators import SimpleErrorResponseModel


def build_openapi_responses(
    error_map: ErrorMap,
    default_response_model: type[Any] = SimpleErrorResponseModel,
) -> dict[Union[int, str], dict[str, Any]]:
    responses: dict[Union[int, str], dict[str, Any]] = {}

    for value in error_map.values():
        if isinstance(value, int):
            status_code = value
            response_model: type[Any] = default_response_model
        else:
            status_code = value.status
            response_model = (
                value.translator.error_response_model_cls
                if value.translator is not None
                else default_response_model
            )
        responses[status_code] = {"model": response_model}

    return responses
