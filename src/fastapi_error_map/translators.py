from abc import abstractmethod
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)


class ErrorTranslator(Protocol, Generic[T_co]):
    """
    Protocol for converting exception into response data and OpenAPI schema.

    Must define:

    - `from_error(err)` — returns serializable object
    - `error_response_model_cls` — returns model class used for schema

    For simple response like {"error": "..."}, import and use
    `SimpleErrorResponseModel` from the public API.

    Example:

        >>> class MyTranslator(ErrorTranslator[SimpleErrorResponseModel]):
        ...     def from_error(self, err: Exception) -> SimpleErrorResponseModel:
        ...         return SimpleErrorResponseModel(error="...")
        ...
        ...     @property
        ...     def error_response_model_cls(self) -> type[SimpleErrorResponseModel]:
        ...         return SimpleErrorResponseModel
    """

    @property
    @abstractmethod
    def error_response_model_cls(self) -> type[T_co]: ...

    @abstractmethod
    def from_error(self, err: Exception) -> T_co: ...


@dataclass
class SimpleErrorResponseModel:
    """
    Default response model used when no translator is provided.

    Can also be used in custom translators:

        >>> class MyTranslator(ErrorTranslator[SimpleErrorResponseModel]):
        ...     def from_error(self, err: Exception) -> SimpleErrorResponseModel:
        ...         return SimpleErrorResponseModel(error="...")
        ...
        ...     @property
        ...     def error_response_model_cls(self) -> type[SimpleErrorResponseModel]:
        ...         return SimpleErrorResponseModel

    Produces: {"error": "..."}
    """

    error: str


class DefaultClientErrorTranslator(ErrorTranslator[SimpleErrorResponseModel]):
    @property
    def error_response_model_cls(self) -> type[SimpleErrorResponseModel]:
        return SimpleErrorResponseModel

    def from_error(self, err: Exception) -> SimpleErrorResponseModel:
        return SimpleErrorResponseModel(error=str(err))


class DefaultServerErrorTranslator(ErrorTranslator[SimpleErrorResponseModel]):
    @property
    def error_response_model_cls(self) -> type[SimpleErrorResponseModel]:
        return SimpleErrorResponseModel

    def from_error(self, _err: Exception) -> SimpleErrorResponseModel:
        return SimpleErrorResponseModel(error="Internal server error.")
