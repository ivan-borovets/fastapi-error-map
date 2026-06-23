import functools
import operator
import warnings
from typing import Any, Final

from fastapi_error_map.rules import CompiledErrorMap, ResolvedRule
from fastapi_error_map.types_ import ErrorMapWarning, OpenApiResponses

_JSON: Final[str] = "application/json"
_STRING_HEADER_SCHEMA: Final[dict[str, Any]] = {"schema": {"type": "string"}}


def _group_by_status(compiled: CompiledErrorMap) -> dict[int, list[ResolvedRule]]:
    grouped: dict[int, list[ResolvedRule]] = {}
    for resolved in compiled.values():
        grouped.setdefault(resolved.status, []).append(resolved)
    return grouped


def _warn_on_duplicate_example_keys(status: int, rules: list[ResolvedRule]) -> None:
    seen: set[str] = set()
    for rule in rules:
        for key in rule.openapi_examples or {}:
            if key in seen:
                warnings.warn(
                    f"status {status}: duplicate OpenAPI example key {key!r} — "
                    f"a later rule overwrites an earlier one",
                    ErrorMapWarning,
                    stacklevel=2,
                )
            seen.add(key)


def _build_response_entry(rules: list[ResolvedRule]) -> dict[str, Any]:
    # one model -> itself; several on one status -> A | B (FastAPI renders anyOf)
    model = functools.reduce(operator.or_, (rule.openapi_model for rule in rules))
    entry: dict[str, Any] = {"model": model}

    descriptions: dict[str, None] = {}
    header_schemas: dict[str, Any] = {}
    examples: dict[str, Any] = {}
    for rule in rules:
        if rule.openapi_description is not None:
            descriptions[rule.openapi_description] = None
        for name in rule.static_headers or {}:
            header_schemas[name] = _STRING_HEADER_SCHEMA
        examples.update(rule.openapi_examples or {})

    if descriptions:
        entry["description"] = "\n".join(descriptions)
    if header_schemas:
        entry["headers"] = header_schemas
    if examples:
        entry["content"] = {_JSON: {"examples": examples}}
    return entry


def build_openapi_responses(
    compiled: CompiledErrorMap,
    responses: OpenApiResponses | None = None,
) -> OpenApiResponses:
    grouped = _group_by_status(compiled)
    for status, rules in grouped.items():
        _warn_on_duplicate_example_keys(status, rules)
    built: OpenApiResponses = {
        status: _build_response_entry(rules) for status, rules in grouped.items()
    }
    return {**built, **(responses or {})}
