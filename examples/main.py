from fastapi import FastAPI

from examples.errors import (
    AuthorizationError,
    OutOfStockError,
    OutOfStockTranslator,
    notify,
)
from fastapi_error_map import ErrorAwareRouter, rule

# --- README ---
# A seamless replacement for APIRouter with error mapping support
router = ErrorAwareRouter()


@router.get(
    "/stock",
    error_map={
        # Minimal rule: return 401 and respond with {"error": "..."}
        # using default translator
        AuthorizationError: 401,
        # Full rule: return 409 and respond with custom JSON
        # using custom translator, and trigger side effect
        OutOfStockError: rule(
            status=409,
            translator=OutOfStockTranslator(),
            on_error=notify,
        ),
    },
)
def check_stock(user_id: int = 0) -> None:
    if user_id == 0:
        raise AuthorizationError
    raise OutOfStockError("No items available.")


# --- /README ---


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app=create_app(),
        port=8000,
        reload=False,
    )
