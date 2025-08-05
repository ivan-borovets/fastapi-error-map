from fastapi_error_map import ErrorTranslator


class DummyClientErrorTranslator(ErrorTranslator[dict[str, str]]):
    @property
    def error_response_model_cls(self) -> type[dict[str, str]]:
        return dict

    def from_error(self, err: Exception) -> dict[str, str]:
        return {"error": f"client:{err}"}


class DummyServerErrorTranslator(ErrorTranslator[dict[str, str]]):
    @property
    def error_response_model_cls(self) -> type[dict[str, str]]:
        return dict

    def from_error(self, _err: Exception) -> dict[str, str]:
        return {"error": "internal"}


class CustomTranslator(ErrorTranslator[dict[str, str]]):
    @property
    def error_response_model_cls(self) -> type[dict[str, str]]:
        return dict

    def from_error(self, _err: Exception) -> dict[str, str]:
        return {"msg": "explicit"}
