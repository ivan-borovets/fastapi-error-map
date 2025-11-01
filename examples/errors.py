import asyncio
from dataclasses import dataclass

from fastapi_error_map.translators import ErrorTranslator


class OutOfStockError(Exception):
    pass


class AuthorizationError(Exception):
    pass


@dataclass
class ErrorResponseModel:
    error: str


class OutOfStockTranslator(ErrorTranslator[ErrorResponseModel]):
    def from_error(self, err: Exception) -> ErrorResponseModel:
        return ErrorResponseModel(error=str(err))

    @property
    def error_response_model_cls(self):
        return ErrorResponseModel


async def notify(err: Exception) -> None:
    await asyncio.sleep(0)
    print("Notified admin:", err)
