import pytest
import state
from state import load_known_ids, save_known_ids


def test_load_returns_empty_set_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_FILE", str(tmp_path / "known.json"))
    assert load_known_ids() == set()


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_FILE", str(tmp_path / "known.json"))
    save_known_ids({"abc", "def"})
    assert load_known_ids() == {"abc", "def"}


def test_overwrite_replaces_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_FILE", str(tmp_path / "known.json"))
    save_known_ids({"old"})
    save_known_ids({"new1", "new2"})
    assert load_known_ids() == {"new1", "new2"}
