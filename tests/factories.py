from collections.abc import Mapping
from typing import Any, ClassVar

from typing_extensions import TypedDict


class StructuredError(Exception):
    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        if message is None:
            super().__init__()
        else:
            super().__init__(message)
        self.code = code
        self.details = details


class MalformedError(Exception):
    code: ClassVar[object] = 123
    details: ClassVar[object] = ["not", "a", "mapping"]


class PlainError(Exception): ...


class ClientError(Exception): ...


class ServerError(Exception): ...


class ParentError(Exception): ...


class ChildError(ParentError): ...


class OtherClientError(Exception): ...


class TeapotResponse(TypedDict):
    reason: str


class OtherResponse(TypedDict):
    detail: str


def teapot(err: Exception) -> TeapotResponse:
    return TeapotResponse(reason=str(err))


def other(err: Exception) -> OtherResponse:
    return OtherResponse(detail=str(err))
