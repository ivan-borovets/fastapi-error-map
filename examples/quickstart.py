"""Map exceptions to responses in the route declaration.

The handler raises; the router turns each exception into its status and body.

Run: python -m examples.quickstart
- GET /items/0/ -> 404 {"error": "item 0 not found"}
"""

from fastapi import FastAPI
from pydantic import BaseModel
from starlette import status

from fastapi_error_map import ErrorAwareRouter


class ItemNotFoundError(Exception): ...


class Item(BaseModel):
    item_id: int


def make_app() -> FastAPI:
    router = ErrorAwareRouter()

    @router.get(
        "/items/{item_id}/",
        error_map={
            ItemNotFoundError: status.HTTP_404_NOT_FOUND,
        },
    )
    def get_item(item_id: int) -> Item:
        if item_id == 0:
            raise ItemNotFoundError(f"item {item_id} not found")
        return Item(item_id=item_id)

    app = FastAPI()
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(make_app())
