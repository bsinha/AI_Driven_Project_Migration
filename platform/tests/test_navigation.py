"""Tests for main navigation helpers."""

from __future__ import annotations

from migrate_framework.ui.navigation import ensure_main_tab, set_main_tab


class _Session(dict):
    def __getattr__(self, name: str):
        return self[name]

    def __setattr__(self, name: str, value):
        self[name] = value


def test_ensure_main_tab_resets_invalid_selection(monkeypatch) -> None:
    session = _Session(main_tab="Governance")
    monkeypatch.setattr("migrate_framework.ui.navigation.st.session_state", session)
    ensure_main_tab(["Dashboard", "Assessment"])
    assert session.main_tab == "Dashboard"


def test_set_main_tab_updates_session(monkeypatch) -> None:
    session = _Session(main_tab="Dashboard")
    monkeypatch.setattr("migrate_framework.ui.navigation.st.session_state", session)
    set_main_tab("Assessment")
    assert session.main_tab == "Assessment"
