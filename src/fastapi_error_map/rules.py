from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

from fastapi_error_map.translator_policy import pick_translator_for_status
from fastapi_error_map.translators import ErrorTranslator


@dataclass
class Rule:
    status: int
    translator: Optional[ErrorTranslator[Any]]
    on_error: Optional[Callable[[Exception], None]]


def rule(
    *,
    status: int,
    translator: Optional[ErrorTranslator[Any]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> Rule:
    """
    Defines full error handling rule for use in `error_map`.

    Allows setting:

    - `status` — HTTP status code to return
    - `translator` — optional translator to produce response content
    - `on_error` — optional function to run when exception occurs

    Example:
        >>> error_map = {
        ...     MyError: rule(
        ...         status=409,
        ...         translator=MyTranslator(),
        ...         on_error=notify_admin,
        ...     )
        ... }
    """
    return Rule(status=status, translator=translator, on_error=on_error)


ErrorMap = dict[type[Exception], Union[int, Rule]]


@dataclass
class ResolvedRule:
    status: int
    translator: ErrorTranslator[Any]
    on_error: Optional[Callable[[Exception], None]]


def resolve_rule_for_error(
    *,
    error: Exception,
    error_map: ErrorMap,
    default_client_error_translator: ErrorTranslator[Any],
    default_server_error_translator: ErrorTranslator[Any],
    default_on_error: Optional[Callable[[Exception], None]] = None,
) -> ResolvedRule:
    try:
        status_or_rule = error_map[type(error)]
    except KeyError:
        raise RuntimeError(f"No rule defined for {type(error).__name__}") from error

    if isinstance(status_or_rule, int):
        status, translator, on_error = status_or_rule, None, default_on_error
    else:
        status, translator, on_error = (
            status_or_rule.status,
            status_or_rule.translator,
            status_or_rule.on_error or default_on_error,
        )

    if translator is None:
        translator = pick_translator_for_status(
            status=status,
            default_client_error_translator=default_client_error_translator,
            default_server_error_translator=default_server_error_translator,
        )

    return ResolvedRule(
        status=status,
        translator=translator,
        on_error=on_error,
    )
