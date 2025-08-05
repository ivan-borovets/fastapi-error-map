import pytest

from fastapi_error_map.translators import (
    DefaultClientErrorTranslator,
    DefaultServerErrorTranslator,
    ErrorTranslator,
    SimpleErrorResponseModel,
)


def test_client_error_translator_returns_model_with_error_message() -> None:
    error_message = "some message"
    error = ValueError(error_message)
    sut = DefaultClientErrorTranslator()

    response = sut.from_error(error)

    assert isinstance(response, SimpleErrorResponseModel)
    assert error_message in response.error


def test_server_error_translator_returns_model_without_error_message() -> None:
    error_message = "some message"
    error = ValueError(error_message)
    sut = DefaultServerErrorTranslator()

    response = sut.from_error(error)

    assert isinstance(response, SimpleErrorResponseModel)
    assert error_message not in response.error


@pytest.mark.parametrize(
    "translator",
    [
        DefaultClientErrorTranslator(),
        DefaultServerErrorTranslator(),
    ],
)
def test_default_translator_exposes_simple_response_model_class(
    translator: ErrorTranslator[SimpleErrorResponseModel],
) -> None:
    assert issubclass(translator.error_response_model_cls, SimpleErrorResponseModel)
