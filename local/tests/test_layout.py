from pathlib import Path

import pytest


def test_state_path_uses_explicit_temp_override_without_mutating_existing_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from fiverr_seller_os import __version__, state_path

    state_dir = tmp_path / "existing-state"
    state_dir.mkdir()
    marker = state_dir / "keep.txt"
    marker.write_text("unchanged", encoding="utf-8")
    monkeypatch.setenv("FIVERR_SELLER_OS_STATE_DIR", str(state_dir))

    resolved_state_path = state_path()
    repeated_state_path = state_path()

    assert __version__ == "0.1.0"
    assert resolved_state_path == state_dir
    assert repeated_state_path == state_dir
    assert marker.read_text(encoding="utf-8") == "unchanged"
    assert sorted(path.name for path in state_dir.iterdir()) == ["keep.txt"]


def test_state_path_default_is_a_user_writable_application_support_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fiverr_seller_os import state_path

    monkeypatch.delenv("FIVERR_SELLER_OS_STATE_DIR", raising=False)

    resolved_state_path = state_path()

    assert resolved_state_path == Path.home() / "Library" / "Application Support" / "FiverrSellerOS"
    assert resolved_state_path.is_relative_to(Path.home())
