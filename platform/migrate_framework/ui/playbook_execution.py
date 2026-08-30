"""Streamlit UI for assisted playbook task execution."""

from __future__ import annotations

from typing import Any

import streamlit as st

from migrate_framework.migration.task_assistant import (
    apply_proposal_files,
    assist_playbook_task,
    get_playbook_tasks,
    get_proposal,
    store_proposal,
    update_task_status,
)
from migrate_framework.models import MigrationProject
from migrate_framework.pipeline.project_store import ProjectStore


def _phase_filter_options(tasks: list[dict[str, Any]]) -> list[str]:
    phases = sorted({task.get("phase") for task in tasks if task.get("phase") is not None})
    options = ["All phases", "Cross-cutting"]
    options.extend(f"Phase {phase}" for phase in phases)
    return options


def _task_matches_phase(task: dict[str, Any], selected: str) -> bool:
    if selected == "All phases":
        return True
    if selected == "Cross-cutting":
        return task.get("phase") is None
    phase_num = int(selected.replace("Phase ", ""))
    return task.get("phase") == phase_num


def render_playbook_execution(project: MigrationProject, store: ProjectStore) -> None:
    tasks = get_playbook_tasks(project)
    if not tasks:
        st.info("Run the **playbook** stage first to generate migration tasks.")
        return

    st.subheader("Assisted task execution")
    st.caption(
        "Generate reviewable diffs for playbook tasks. Nothing is written until you approve selected files."
    )

    phase_choice = st.selectbox("Filter by phase", _phase_filter_options(tasks), key="playbook-phase-filter")
    filtered = [task for task in tasks if _task_matches_phase(task, phase_choice)]

    pending = sum(1 for task in filtered if task.get("status") == "pending")
    done = sum(1 for task in filtered if task.get("status") == "completed")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tasks in view", len(filtered))
    c2.metric("Pending", pending)
    c3.metric("Completed", done)

    for task in filtered:
        status = task.get("status", "pending")
        phase_label = f"Phase {task['phase']}" if task.get("phase") else "Cross-cutting"
        header = f"{task.get('task')} — _{task.get('owner', 'team')}_ · {phase_label} · **{status}**"

        with st.expander(header, expanded=False):
            st.markdown(f"**Category:** {task.get('category', '—')}")
            if task.get("context"):
                st.markdown(f"**Context:** {task.get('context')}")

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                assist = st.button("Generate assistance", key=f"assist-{task['id']}")
            with col_b:
                complete = st.button("Mark complete", key=f"complete-{task['id']}")
            with col_c:
                reset = st.button("Reset to pending", key=f"reset-{task['id']}")

            if assist:
                proposal = assist_playbook_task(project, task)
                store_proposal(project, proposal)
                update_task_status(project, task["id"], "in_review")
                store.save_project(project)
                st.rerun()

            if complete:
                update_task_status(project, task["id"], "completed")
                store.save_project(project)
                st.rerun()

            if reset:
                update_task_status(project, task["id"], "pending")
                store.save_project(project)
                st.rerun()

            proposal = get_proposal(project, task["id"])
            if not proposal:
                continue

            st.markdown(proposal.get("guidance", ""))
            files = proposal.get("files") or []
            if not files:
                continue

            st.markdown("**Proposed changes (review diffs before applying)**")
            selected_paths: set[str] = set()
            for index, file_entry in enumerate(files):
                path = file_entry.get("path", "")
                st.markdown(f"`{file_entry.get('action', 'create')}` **{path}**")
                st.code(file_entry.get("diff", ""), language="diff")
                if st.checkbox(f"Approve `{path}`", key=f"approve-file-{task['id']}-{index}", value=True):
                    selected_paths.add(path)

            if st.button("Apply approved files", key=f"apply-{task['id']}", type="primary"):
                written = apply_proposal_files(project, proposal, selected_paths)
                if written:
                    update_task_status(project, task["id"], "completed")
                    store.save_project(project)
                    st.success(f"Applied {len(written)} file(s): {', '.join(written)}")
                    st.rerun()
                else:
                    st.warning("Select at least one file to apply.")
