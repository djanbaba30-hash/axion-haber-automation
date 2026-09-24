from apps.axion_local import preferences


def test_remember_uses_saved_values_and_fixes_invalid_choices(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path))
    preferences.save_preferences({"speed": 0.9, "model": "silinmiş-model"})
    state = {}
    preferences.remember(state, {"speed": 1.11, "model": "A", "boost": True}, {"model": ["A", "B"]})
    assert state == {"speed": 0.9, "model": "A", "boost": True}


def test_session_value_wins_over_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path))
    preferences.save_preferences({"speed": 0.9})
    state = {"speed": 1.05}
    preferences.remember(state, {"speed": 1.11})
    assert state["speed"] == 1.05


def test_persist_writes_only_on_change(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path))
    state = {"speed": 1.0}
    preferences.persist(state, ["speed"])
    assert preferences.load_preferences() == {"speed": 1.0}
    preferences.preferences_path().write_text("{}", encoding="utf-8")
    preferences.persist(state, ["speed"])
    assert preferences.load_preferences() == {}
    state["speed"] = 1.2
    preferences.persist(state, ["speed"])
    assert preferences.load_preferences() == {"speed": 1.2}


def test_corrupt_file_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path))
    preferences.preferences_path().write_text("[bozuk", encoding="utf-8")
    assert preferences.load_preferences() == {}
