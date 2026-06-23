from typing import Final

from starlette import status as http_status

CLIENT_ERROR_FLOOR: Final[int] = 400
SERVER_ERROR_FLOOR: Final[int] = 500
ERROR_CEILING: Final[int] = 600

_NAME_BY_STATUS: Final[dict[int, str]] = {
    getattr(http_status, name): name
    for name in http_status.__all__
    if name.startswith("HTTP_") and isinstance(getattr(http_status, name), int)
}


def status_name(status: int) -> str:
    return _NAME_BY_STATUS.get(status, f"HTTP_{status}_UNKNOWN")
