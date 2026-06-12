"""Built-in translator factories — the shelf for response formats.

One module per format (``simple``, ``structured``, ...).
A new stock format is a new module plus one reexport line here.
Import from here or from the package root.
"""

from fastapi_error_map.translator_factories.simple import SimpleErrorResponse, simple
from fastapi_error_map.translator_factories.structured import (
    StructuredErrorResponse,
    structured,
)

__all__ = [
    "SimpleErrorResponse",
    "StructuredErrorResponse",
    "simple",
    "structured",
]
