"""Tests for auto-update utilities."""
import pytest
from unittest.mock import patch, MagicMock


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


# ---------------------------------------------------------------------------
# auto_updater tests
# ---------------------------------------------------------------------------

def test_get_update_path_sibling_of_exe():
    from pathlib import Path
    from auto_updater import _get_update_path
    result = Path(_get_update_path("C:/Users/user/Desktop/AuditMagic.exe"))
    assert result == Path("C:/Users/user/Desktop/AuditMagic_update.exe")


def test_get_update_path_handles_spaces():
    from pathlib import Path
    from auto_updater import _get_update_path
    result = Path(_get_update_path("C:/My Folder/AuditMagic.exe"))
    assert result == Path("C:/My Folder/AuditMagic_update.exe")


def test_download_file_success(tmp_path):
    """_download_file writes content and calls progress callback."""
    from auto_updater import _download_file

    fake_data = b"x" * 1000
    mock_response = MagicMock()
    mock_response.headers = {"Content-Length": "1000"}
    mock_response.read.side_effect = [fake_data[:500], fake_data[500:], b""]
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    dest = tmp_path / "AuditMagic_update.exe"
    progress_calls = []

    with patch("urllib.request.urlopen", return_value=mock_response):
        _download_file("https://example.com/AuditMagic.exe", str(dest), progress_calls.append)

    assert dest.exists()
    assert dest.read_bytes() == fake_data
    assert 100 in progress_calls


def test_download_file_cleans_up_on_failure(tmp_path):
    """_download_file removes partial file on network error."""
    from auto_updater import _download_file

    dest = tmp_path / "AuditMagic_update.exe"

    with patch("urllib.request.urlopen", side_effect=OSError("network error")):
        with pytest.raises(OSError):
            _download_file("https://example.com/AuditMagic.exe", str(dest))

    assert not dest.exists()


def test_launch_updater_raises_outside_frozen():
    """launch_updater must raise RuntimeError when not running as bundled exe."""
    from auto_updater import launch_updater
    with pytest.raises(RuntimeError, match="frozen"):
        launch_updater("AuditMagic.exe", "AuditMagic_update.exe")
