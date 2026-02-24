from unittest.mock import patch

import pytest
from fastapi.datastructures import Default

from fastapi_error_map.routing import _with_strict_content_type  # noqa: PLC2701


def test_with_strict_content_type_passes_value_when_supported() -> None:
    with patch("fastapi_error_map.routing._HAS_STRICT_CONTENT_TYPE", True):
        result = _with_strict_content_type(False, {"foo": "bar"})

    assert result == {"foo": "bar", "strict_content_type": False}


def test_with_strict_content_type_passes_default_when_supported() -> None:
    with patch("fastapi_error_map.routing._HAS_STRICT_CONTENT_TYPE", True):
        result = _with_strict_content_type(Default(True), {"foo": "bar"})

    assert result == {"foo": "bar", "strict_content_type": Default(True)}


def test_with_strict_content_type_skips_default_when_unsupported() -> None:
    with patch("fastapi_error_map.routing._HAS_STRICT_CONTENT_TYPE", False):
        result = _with_strict_content_type(Default(True), {"foo": "bar"})

    assert result == {"foo": "bar"}


def test_with_strict_content_type_raises_when_explicit_on_old_version() -> None:
    with (
        patch("fastapi_error_map.routing._HAS_STRICT_CONTENT_TYPE", False),
        pytest.raises(TypeError, match=r"requires FastAPI >=0\.132\.0"),
    ):
        _with_strict_content_type(False, {})


def test_with_strict_content_type_does_not_mutate_input() -> None:
    original = {"foo": "bar"}
    with patch("fastapi_error_map.routing._HAS_STRICT_CONTENT_TYPE", True):
        result = _with_strict_content_type(True, original)

    assert "strict_content_type" not in original
    assert "strict_content_type" in result
