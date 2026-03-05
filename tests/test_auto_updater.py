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

def test_download_path_is_in_temp():
    """_DOWNLOAD_PATH must be in the system temp directory."""
    import tempfile
    from pathlib import Path
    from auto_updater import _DOWNLOAD_PATH
    assert _DOWNLOAD_PATH.parent == Path(tempfile.gettempdir())
    assert _DOWNLOAD_PATH.name == "AuditMagic_update.exe"


def test_old_path_is_in_temp():
    """_OLD_PATH must be in the system temp directory."""
    import tempfile
    from pathlib import Path
    from auto_updater import _OLD_PATH
    assert _OLD_PATH.parent == Path(tempfile.gettempdir())
    assert _OLD_PATH.name == "AuditMagic.old.exe"


def test_download_file_success(tmp_path):
    """_download_file writes content and calls progress callback."""
    from unittest.mock import MagicMock, patch
    from auto_updater import _download_file

    fake_data = b"x" * 1000
    mock_response = MagicMock()
    mock_response.headers = {"Content-Length": "1000"}
    mock_response.iter_content.return_value = [fake_data[:500], fake_data[500:]]
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    dest = tmp_path / "AuditMagic_update.exe"
    progress_calls = []

    with patch("requests.get", return_value=mock_response):
        _download_file("https://example.com/AuditMagic.exe", dest, progress_calls.append)

    assert dest.exists()
    assert dest.read_bytes() == fake_data
    assert 100 in progress_calls


def test_download_file_cleans_up_on_failure(tmp_path):
    """_download_file removes partial file on network error."""
    from unittest.mock import patch
    from auto_updater import _download_file

    dest = tmp_path / "AuditMagic_update.exe"

    with patch("requests.get", side_effect=OSError("network error")):
        with pytest.raises(OSError):
            _download_file("https://example.com/AuditMagic.exe", dest)

    assert not dest.exists()


def test_apply_update_raises_outside_frozen():
    """apply_update must raise RuntimeError when not running as bundled exe."""
    from auto_updater import apply_update
    with pytest.raises(RuntimeError, match="frozen"):
        apply_update("AuditMagic.exe")


def test_cleanup_old_update_deletes_file(tmp_path):
    """cleanup_old_update deletes _OLD_PATH if it exists."""
    from unittest.mock import patch
    from pathlib import Path
    from auto_updater import cleanup_old_update

    fake_old = tmp_path / "AuditMagic.old.exe"
    fake_old.write_bytes(b"old")

    with patch("auto_updater._OLD_PATH", fake_old):
        cleanup_old_update()

    assert not fake_old.exists()


def test_cleanup_old_update_silent_when_missing(tmp_path):
    """cleanup_old_update does not raise if _OLD_PATH does not exist."""
    from unittest.mock import patch
    from pathlib import Path
    from auto_updater import cleanup_old_update

    missing = tmp_path / "AuditMagic.old.exe"
    # Do not create the file

    with patch("auto_updater._OLD_PATH", missing):
        cleanup_old_update()  # must not raise
