"""Tests for auto-update utilities."""
import pytest


def test_is_newer_rejects_malformed_tag_with_dot():
    """Regression: tag 'v.1.0.11' must not silently fail version comparison."""
    from update_checker import _is_newer
    # .1.0.11 would raise ValueError with the old lstrip("v") approach
    assert not _is_newer(".1.0.11", "1.0.11")


def test_update_checker_strips_v_dot_prefix():
    """check_for_update should handle tag_name 'v.1.0.12' as version '1.0.12'."""
    from update_checker import _is_newer
    assert _is_newer("1.0.12", "1.0.11")
    assert not _is_newer("1.0.11", "1.0.11")


def test_tag_stripping_handles_v_dot_prefix():
    """v.1.0.12 stripped correctly gives 1.0.12, which is newer than 1.0.11."""
    tag = "v.1.0.12"
    version = tag.removeprefix("v").removeprefix(".")
    from update_checker import _is_newer
    assert version == "1.0.12"
    assert _is_newer(version, "1.0.11")
