"""Governance UI: gates, decision log, waivers, V&V, role views."""

from __future__ import annotations

from typing import Any

import streamlit as st

from migrate_framework.governance_enums import GATE_REASON_CODES, GateDecisionStatus
from migrate_framework.models import MigrationProject, PipelineStage
from migrate_framework.pipeline.governance import (
    confidence_threshold,
    needs_escalation,
    stage_summary_metrics,
)
from migrate_framework.pipeline.orchestrator import PipelineOrchestrator
from migrate_framework.reporting.pipeline_report import generate_markdown_report


ROLE_VIEWS: dict[str, list[str]] = {
    "architect": ["governance", "gates", "adrs", "vv", "analytics"],
    "engineer": ["playbook", "analytics", "vv"],
    "program": ["plan", "analytics", "gates"],
}


def render_role_selector() -> str:
    if "ui_role" not in st.session_state:
        st.session_state.ui_role = "architect"
    return st.sidebar.selectbox(
        "View as",
        options=list(ROLE_VIEWS.keys()),
        format_func=lambda r: r.title(),
        key="ui_role_select",
    )


def role_allows(role: str, section: str) -> bool:
    return section in ROLE_VIEWS.get(role, [])


def render_escalation_banner(project: MigrationProject) -> None:
    if needs_escalation(project):
        st.error(
            "Architecture board escalation recommended — repeated gate rejections detected. "
            "Review decision log before proceeding."
        )


def render_decision_log(project: MigrationProject) -> None:
    st.subheader("Decision audit trail")
    records = project.decision_log()
    if not records:
        st.info("No governance decisions recorded yet.")
        return

    rows = [
        {
            "when": entry.decision_at.isoformat(),
            "stage": entry.stage.value,
            "action": entry.action.value,
            "by": entry.decision_by,
            "reason": entry.reason_code or "—",
            "detail": (entry.reason_text or entry.notes or "—")[:120],
            "round": entry.iteration_round,
        }
        for entry in reversed(records[-50:])
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_waiver_registry(project: MigrationProject) -> None:
    waivers = project.waiver_registry()
    if not waivers:
        return
    st.subheader("Waiver registry")
    st.dataframe(
        [
            {
                "item": w.title,
                "type": w.item_type,
                "reason": w.reason_code,
                "by": w.waived_by,
                "when": w.waived_at.isoformat(),
            }
            for w in waivers
        ],
        use_container_width=True,
        hide_index=True,
    )


def _gate_action_form(
    orch: PipelineOrchestrator,
    project: MigrationProject,
    stage: PipelineStage,
    action: str,
) -> None:
    prefix = f"{action}-{stage.value}"
    with st.form(prefix):
        reason_code = st.selectbox("Reason code", GATE_REASON_CODES, key=f"{prefix}-code")
        reason_text = st.text_area(
            "Reason (required for reject / waive / modify)",
            key=f"{prefix}-text",
        )
        notes = st.text_input("Notes (optional)", key=f"{prefix}-notes")
        submitted = st.form_submit_button(action.title())

    if submitted:
        try:
            if action == "approve":
                orch.approve(
                    project.id,
                    stage,
                    approved_by=st.session_state.get("decision_by", "operator"),
                    notes=notes or None,
                    reason_code=reason_code if reason_code != "other" else None,
                    reason_text=reason_text or None,
                    allow_low_confidence=st.session_state.get("allow_low_confidence", False),
                )
            elif action == "reject":
                orch.reject(
                    project.id,
                    stage,
                    st.session_state.get("decision_by", "operator"),
                    reason_code,
                    reason_text,
                    notes=notes or None,
                )
            elif action == "waive":
                orch.waive(
                    project.id,
                    stage,
                    st.session_state.get("decision_by", "operator"),
                    reason_code,
                    reason_text,
                    notes=notes or None,
                )
            st.success(f"Recorded {action} for {stage.value}")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def render_gate_controls(orch: PipelineOrchestrator, project: MigrationProject) -> None:
    st.subheader("Approval gates")
    st.caption(
        f"Confidence approval threshold: {confidence_threshold():.0%}. "
        "Reject and waive require a reason. Pipeline blocks until required gates are approved or waived."
    )

    st.session_state.decision_by = st.text_input("Decision by (name)", value=st.session_state.get("decision_by", "architect"))
    st.session_state.allow_low_confidence = st.checkbox(
        "Allow approve below confidence threshold",
        value=st.session_state.get("allow_low_confidence", False),
    )

    for gate in project.approval_gates:
        with st.expander(f"{gate.stage.value} · {gate.status.value} · round {gate.iteration_round}", expanded=False):
            st.write(f"Required: **{gate.required}** · Approved flag: **{gate.approved}**")
            if gate.reason_text:
                st.warning(gate.reason_text)
            if gate.required and not gate.is_cleared():
                tab_a, tab_r, tab_w = st.tabs(["Approve", "Reject", "Waive"])
                with tab_a:
                    _gate_action_form(orch, project, gate.stage, "approve")
                with tab_r:
                    _gate_action_form(orch, project, gate.stage, "reject")
                with tab_w:
                    _gate_action_form(orch, project, gate.stage, "waive")


def render_as_is_to_be(project: MigrationProject) -> None:
    st.subheader("AS-IS → TO-BE summary")
    adrs = project.metadata.get("adrs", [])
    if not adrs:
        st.info("Run **recommend** to generate ADRs with AS-IS / TO-BE previews.")
        return

    rows = [
        {
            "adr": adr.get("title"),
            "mandatory": adr.get("mandatory", False),
            "confidence": adr.get("confidence"),
            "as_is": adr.get("as_is_summary", "—"),
            "to_be": adr.get("to_be_preview", "—"),
            "benefit": adr.get("benefit_if_accepted", "—"),
            "risk_if_rejected": adr.get("risk_if_rejected", "—"),
        }
        for adr in adrs
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_vv_matrix(project: MigrationProject) -> None:
    st.subheader("Verification & validation — capability matrix")
    summary = project.metadata.get("capability_matrix_summary", {})
    matrix = project.metadata.get("capability_matrix", [])
    if not matrix:
        st.info("Capability matrix is generated when **recommend** runs (after ingest evidence).")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Capabilities", summary.get("total_capabilities", 0))
    c2.metric("Mapped", summary.get("mapped", 0))
    c3.metric("Coverage", f"{summary.get('coverage_pct', 0)}%")

    gaps = [row for row in matrix if row.get("status") == "gap"]
    if gaps:
        st.warning(f"{len(gaps)} capability gap(s) — SME validation required before cutover.")
        st.dataframe(gaps[:25], use_container_width=True, hide_index=True)
    else:
        st.dataframe(matrix[:25], use_container_width=True, hide_index=True)


def render_stage_analytics(project: MigrationProject) -> None:
    st.subheader("Stage analytics")
    rows = [stage_summary_metrics(project, stage) for stage in PipelineStage]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_embedded_report(project: MigrationProject) -> None:
    st.subheader("Stakeholder report (preview)")
    md = generate_markdown_report(project)
    st.markdown(md[:12000] + ("\n\n…" if len(md) > 12000 else ""))


def render_evidence_gap_request(orch: PipelineOrchestrator, project: MigrationProject) -> None:
    with st.form("evidence-gap"):
        description = st.text_area("Describe missing evidence or SME input needed")
        if st.form_submit_button("Add evidence-gap playbook task"):
            if description.strip():
                orch.request_evidence(project.id, description.strip(), st.session_state.get("decision_by", "operator"))
                st.success("Evidence gap task added to playbook.")
                st.rerun()
            else:
                st.error("Description required.")


def render_governance_panel(orch: PipelineOrchestrator, project: MigrationProject, role: str) -> None:
    render_escalation_banner(project)

    if role_allows(role, "governance"):
        render_evidence_gap_request(orch, project)

    if role_allows(role, "gates"):
        render_gate_controls(orch, project)

    render_decision_log(project)
    render_waiver_registry(project)

    if role_allows(role, "adrs"):
        render_as_is_to_be(project)

    if role_allows(role, "vv"):
        render_vv_matrix(project)

    if role_allows(role, "analytics"):
        render_stage_analytics(project)
        with st.expander("Full report preview"):
            render_embedded_report(project)
