"""Batch scope and program-phase setup — UI parity with CLI batch commands."""

from __future__ import annotations

import streamlit as st

from migrate_framework.governance_enums import GATE_REASON_CODES, ITEM_DECISION_STATUSES
from migrate_framework.models import MigrationProject
from migrate_framework.pipeline.orchestrator import PipelineOrchestrator
from migrate_framework.pipeline.scope import (
    _adr_item_id,
    init_program_phases,
    recommend_gate_clear,
    resolve_active_scope,
)


def _scopable_adrs(project: MigrationProject) -> list[dict]:
    return [a for a in project.metadata.get("adrs", []) if a.get("target_context") != "Cross-cutting"]


def render_pilot_scope_wizard(orch: PipelineOrchestrator, project: MigrationProject) -> None:
    """Batch approve selected ADRs and defer the rest (pilot wave)."""
    adrs = _scopable_adrs(project)
    if not adrs:
        return

    st.subheader("Pilot scope wizard (batch)")
    st.caption(
        "Select ADRs to approve for the current wave. Remaining ADRs are deferred in one action — "
        "same as `scope-decide` batch via CLI."
    )

    decision_by = st.session_state.get("decision_by", "architect")
    labels = [f"{a.get('title')} ({a.get('target_context', '—')})" for a in adrs]
    label_to_adr = dict(zip(labels, adrs, strict=True))

    with st.form("pilot-scope-wizard"):
        selected_labels = st.multiselect(
            "ADRs to approve for this wave",
            options=labels,
            help="Unselected ADRs will be deferred to a later program phase.",
        )
        scope_phase = st.number_input("Program phase", min_value=1, value=max(project.current_program_phase(), 1))
        approve_reason = st.text_input("Approval rationale", value="Approved for pilot program scope")
        defer_reason = st.text_input(
            "Deferral rationale (for unselected ADRs)",
            value="Deferred to a later migration wave",
        )
        submitted = st.form_submit_button("Apply pilot scope (batch)")

    if submitted:
        if not selected_labels:
            st.error("Select at least one ADR to approve for the pilot wave.")
            return
        if not defer_reason.strip():
            st.error("Deferral rationale is required for ADRs not in the pilot.")
            return
        try:
            decisions = []
            selected_ids = {_adr_item_id(label_to_adr[label]) for label in selected_labels}
            for adr in adrs:
                item_id = _adr_item_id(adr)
                if item_id in selected_ids:
                    decisions.append(
                        {
                            "item_id": item_id,
                            "item_type": "adr",
                            "decision": "approved",
                            "reason_code": "scope_accepted",
                            "reason_text": approve_reason,
                            "scope_phase": int(scope_phase),
                        }
                    )
                else:
                    decisions.append(
                        {
                            "item_id": item_id,
                            "item_type": "adr",
                            "decision": "deferred",
                            "reason_code": "scope_defer",
                            "reason_text": defer_reason,
                            "scope_phase": int(scope_phase),
                        }
                    )
            orch.decide_scope_items(project.id, decisions, decision_by=decision_by)
            updated = orch.store.load_project(project.id)
            cleared, msg = recommend_gate_clear(updated)
            if cleared:
                st.success(f"Applied pilot scope: {len(selected_labels)} approved, {len(adrs) - len(selected_labels)} deferred.")
            else:
                st.warning(f"Scope applied. {msg}")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    with st.expander("Advanced: custom batch decisions"):
        st.caption("Build arbitrary batch decisions (approve / defer / reject per ADR).")
        with st.form("custom-batch-scope"):
            batch_rows = []
            for adr in adrs:
                item_id = _adr_item_id(adr)
                c1, c2 = st.columns([3, 2])
                with c1:
                    st.text(adr.get("title", item_id))
                with c2:
                    decision = st.selectbox(
                        "Decision",
                        ITEM_DECISION_STATUSES,
                        key=f"batch-dec-{item_id}",
                    )
                batch_rows.append((adr, item_id, decision))
            batch_reason = st.text_area("Reason detail (required for defer/reject)", key="batch-scope-reason")
            batch_phase = st.number_input("Scope phase", min_value=1, value=max(project.current_program_phase(), 1), key="batch-scope-phase")
            if st.form_submit_button("Apply custom batch"):
                if not batch_reason.strip() and any(d in {"deferred", "rejected"} for _, _, d in batch_rows):
                    st.error("Reason detail required when any item is deferred or rejected.")
                else:
                    try:
                        decisions = []
                        for adr, item_id, decision in batch_rows:
                            code = "scope_accepted" if decision == "approved" else "scope_defer"
                            if decision == "rejected":
                                code = "sme_disagreement"
                            decisions.append(
                                {
                                    "item_id": item_id,
                                    "item_type": "adr",
                                    "decision": decision,
                                    "reason_code": code,
                                    "reason_text": batch_reason or f"Batch {decision}",
                                    "scope_phase": int(batch_phase),
                                }
                            )
                        orch.decide_scope_items(project.id, decisions, decision_by=decision_by)
                        st.success("Custom batch scope decisions applied.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))


def render_phase_context_assignment(orch: PipelineOrchestrator, project: MigrationProject) -> None:
    """Assign bounded contexts to a program phase (UI for set_program_phase_contexts)."""
    init_program_phases(project)
    contexts: list[str] = []
    if project.landscape and project.landscape.target_bounded_contexts:
        contexts = [ctx.name for ctx in project.landscape.target_bounded_contexts]

    if not contexts:
        return

    st.subheader("Assign contexts to program phase")
    st.caption("Define which bounded contexts belong to each migration wave.")

    phases = project.metadata.get("program_scope", {}).get("phases", [])
    phase_options = [p.get("phase", 0) for p in phases if p.get("phase", 0) > 0] or [1]

    with st.form("phase-context-assign"):
        target_phase = st.selectbox("Program phase", phase_options, format_func=lambda p: f"Phase {p}")
        selected = st.multiselect("Bounded contexts in this wave", options=contexts)
        if st.form_submit_button("Save phase contexts"):
            orch.set_program_phase_contexts(project.id, int(target_phase), selected)
            st.success(f"Phase {target_phase}: {len(selected)} context(s) assigned.")
            st.rerun()

    active = resolve_active_scope(project)
    if active.get("contexts"):
        st.caption(f"Current in-scope contexts (phase {active.get('phase')}): {', '.join(active['contexts'])}")
