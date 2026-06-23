"""Adopt error mapping into an existing codebase without replacing your routers.

Keep your own ``APIRouter`` — give it our ``route_class`` (the interception
point) and put ``@error_map`` on the endpoint (the map).
Both parts are required.

Run: python -m examples.interop
- GET /accounts/0/ -> 403 {"error": "you do not own this account"}
"""

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel
from starlette import status

from fastapi_error_map import ErrorAwareRoute, error_map


class ForbiddenError(Exception): ...


class Account(BaseModel):
    account_id: int


def make_app() -> FastAPI:
    router = APIRouter(route_class=ErrorAwareRoute)

    @router.get("/accounts/{account_id}/")
    @error_map({ForbiddenError: status.HTTP_403_FORBIDDEN})
    def get_account(account_id: int) -> Account:
        if account_id == 0:
            raise ForbiddenError("you do not own this account")
        return Account(account_id=account_id)

    app = FastAPI()
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(make_app())
