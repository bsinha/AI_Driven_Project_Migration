"""Per-smell governance — accept, defer, or keep open."""

from __future__ import annotations

import streamlit as st

from migrate_framework.governance_enums import GATE_REASON_CODES, SMELL_DECISION_STATUSES
from migrate_framework.models import MigrationProject
from migrate_framework.pipeline.orchestrator import PipelineOrchestrator
from migrate_framework.pipeline.scope import enrich_diagnosis_with_decisions, smell_key


def _smell_rows(project: MigrationProject) -> list[dict]:
    diagnosis = enrich_diagnosis_with_decisions(project)
    rows = []
    for idx, smell in enumerate(diagnosis.get("smells", [])):
        key = smell.get("smell_key") or smell_key(smell, idx)
        rows.append(
            {
                "key": key,
                "type": smell.get("type", "unknown"),
                "status": smell.get("governance_status", "open"),
                "description": smell.get("description", ""),
                "services": smell.get("services") or smell.get("affected_services") or [],
                "smell": smell,
            }
        )
    return rows


def render_smell_batch_actions(orch: PipelineOrchestrator, project: MigrationProject) -> None:
    """Batch accept/defer smells — UI parity with CLI batch."""
    rows = _smell_rows(project)
    open_rows = [r for r in rows if r["status"] == "open"]
    if not open_rows:
        return

    st.markdown("#### Batch smell decisions")
    labels = [f"{r['type']} [{i}] ({r['key']})" for i, r in enumerate(open_rows)]
    label_to_row = dict(zip(labels, open_rows, strict=True))
    decision_by = st.session_state.get("decision_by", "architect")

    with st.form("smell-batch-form"):
        selected = st.multiselect("Smells to update", options=labels)
        decision = st.selectbox("Apply decision to selected", ["accepted", "deferred", "open"])
        reason_code = st.selectbox("Reason", [""] + GATE_REASON_CODES, key="smell-batch-code")
        reason_text = st.text_area("Detail (required for accept/defer)", key="smell-batch-text")
        revisit = st.number_input("Revisit phase (optional)", min_value=0, value=0, key="smell-batch-revisit")
        if st.form_submit_button("Apply batch smell decisions"):
            if not selected:
                st.error("Select at least one smell.")
            elif decision in {"accepted", "deferred"} and not reason_text.strip():
                st.error("Detail required when accepting or deferring.")
            else:
                try:
                    batch = []
                    for label in selected:
                        row = label_to_row[label]
                        batch.append(
                            {
                                "smell_key": row["key"],
                                "smell_type": row["type"],
                                "decision": decision,
                                "affected_services": [str(s) for s in row["services"]],
                                "reason_code": reason_code or None,
                                "reason_text": reason_text or None,
                                "revisit_phase": int(revisit) if revisit else None,
                            }
                        )
                    orch.decide_smell_items(project.id, batch, decision_by=decision_by)
                    st.success(f"Updated {len(batch)} smell(s) to '{decision}'.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def render_smell_governance(orch: PipelineOrchestrator, project: MigrationProject) -> None:
    rows = _smell_rows(project)
    if not rows:
        st.info("Run **diagnose** to detect architectural smells.")
        return

    st.subheader("Smell governance")
    st.caption(
        "Accepted smells remain visible in diagnosis but are excluded from planning. "
        "Use batch actions below or expand individual smells."
    )

    render_smell_batch_actions(orch, project)

    decision_by = st.text_input("Decision by", value=st.session_state.get("decision_by", "architect"), key="smell-decision-by")

    for idx, row in enumerate(rows):
        key = row["key"]
        status = row["status"]
        smell_type = row["type"]
        smell = row["smell"]
        header = f"{smell_type} — **{status}**"
        ui_id = f"{idx}-{key}".replace(":", "-")
        with st.expander(header, expanded=status == "open"):
            st.write(smell.get("description", ""))
            services = row["services"]
            if services:
                st.caption(f"Affected: {', '.join(services)}")

            if status != "open" and smell.get("governance_reason"):
                st.info(smell["governance_reason"])

            with st.form(f"smell-form-{ui_id}"):
                decision = st.selectbox("Decision", SMELL_DECISION_STATUSES, key=f"smell-dec-{ui_id}")
                reason_code = st.selectbox("Reason", [""] + GATE_REASON_CODES, key=f"smell-code-{ui_id}")
                reason_text = st.text_area("Detail", key=f"smell-text-{ui_id}")
                revisit = st.number_input("Revisit phase (optional)", min_value=0, value=0, key=f"smell-revisit-{ui_id}")
                if st.form_submit_button("Record smell decision"):
                    if decision in {"accepted", "deferred"} and not reason_text.strip():
                        st.error("Detail required when accepting or deferring.")
                    else:
                        try:
                            orch.decide_smell_item(
                                project.id,
                                key,
                                smell_type,
                                decision,
                                decision_by=decision_by,
                                affected_services=[str(s) for s in services],
                                reason_code=reason_code or None,
                                reason_text=reason_text or None,
                                revisit_phase=int(revisit) if revisit else None,
                            )
                            st.success(f"Recorded {decision} for {smell_type}")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
