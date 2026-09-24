"""Tests for main navigation helpers."""

from __future__ import annotations

from migrate_framework.ui.navigation import apply_pending_tab_navigation, ensure_main_tab, set_main_tab


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


def test_apply_pending_tab_navigation(monkeypatch) -> None:
    session = _Session(main_tab="Landscape", pending_main_tab="Pipeline")
    monkeypatch.setattr("migrate_framework.ui.navigation.st.session_state", session)
    apply_pending_tab_navigation(["Dashboard", "Pipeline", "Landscape"])
    assert session.main_tab == "Pipeline"
    assert "pending_main_tab" not in session


def test_apply_pending_tab_navigation_invalid_tab_falls_back(monkeypatch) -> None:
    session = _Session(main_tab="Landscape", pending_main_tab="Playbook")
    monkeypatch.setattr("migrate_framework.ui.navigation.st.session_state", session)
    apply_pending_tab_navigation(["Dashboard", "Landscape"])
    assert session.main_tab == "Dashboard"
