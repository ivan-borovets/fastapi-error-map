from dataclasses import dataclass

from fastapi_error_map import ErrorTranslator


@dataclass
class ClientErrorStub:
    error: str


@dataclass
class ServerErrorStub:
    error: str


class DummyClientErrorTranslator(ErrorTranslator[ClientErrorStub]):
    @property
    def error_response_model_cls(self) -> type[ClientErrorStub]:
        return ClientErrorStub

    def from_error(self, err: Exception) -> ClientErrorStub:
        return ClientErrorStub(error=f"client:{err}")


class DummyServerErrorTranslator(ErrorTranslator[ServerErrorStub]):
    @property
    def error_response_model_cls(self) -> type[ServerErrorStub]:
        return ServerErrorStub

    def from_error(self, _err: Exception) -> ServerErrorStub:
        return ServerErrorStub(error="internal")


class CustomTranslator(ErrorTranslator[dict[str, str]]):
    @property
    def error_response_model_cls(self) -> type[dict[str, str]]:
        return dict

    def from_error(self, _err: Exception) -> dict[str, str]:
        return {"msg": "explicit"}
