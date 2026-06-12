"""Static "schema = runtime" guarantee, enforced by mypy.

A ``rule`` whose ``translator`` return type contradicts ``openapi_model`` must be
a type error. The mismatch line is marked ``# type: ignore[arg-type]``; under
``strict``, ``warn_unused_ignores`` fails the file if that ever stops being an
error — catching a silent break of the translator/model binding.
"""

from typing_extensions import TypedDict

from fastapi_error_map import rule


class Found(TypedDict):
    detail: str


class Other(TypedDict):
    other: str


def to_found(err: Exception) -> Found:
    return Found(detail=str(err))


# Matching model — no error.
rule(404, translator=to_found, openapi_model=Found)

# Mismatched model — must be flagged.
rule(404, translator=to_found, openapi_model=Other)  # type: ignore[arg-type]
