"""Streamlit dashboard for migration pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from migrate_framework.models import PIPELINE_STAGE_ORDER, PipelineStage
from migrate_framework.pipeline.orchestrator import PipelineOrchestrator
from migrate_framework.pipeline.project_store import ProjectStore

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

st.set_page_config(page_title="Migrate Framework", layout="wide")
st.title("Microservice → DDD Migration Framework")

store = ProjectStore()
orch = PipelineOrchestrator()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Project")
    projects = store.list_projects()
    selected = st.selectbox("Select project", options=["— new —"] + projects)

    if selected == "— new —":
        name = st.text_input("Project name", value="EuroSA Bank Migration")
        source = st.text_input("Source root", value="../sample-bank")
        landscape = st.text_input("Landscape manifest", value="../sample-bank/landscape-manifest.yaml")
        if st.button("Initialize project"):
            project = orch.init_project(name, str(Path(source).resolve()), str(Path(landscape).resolve()))
            st.success(f"Created project {project.id}")
            st.rerun()
        project = None
    else:
        project = store.load_project(selected)
        st.write(f"**ID:** `{project.id}`")
        st.write(f"**Source:** `{project.source_root}`")
        st.write(f"**Stack:** {project.tech_stack.primary_stack()}")

with col2:
    if project:
        st.subheader("Pipeline Progress")
        completed = {r.stage for r in project.stage_runs if r.status == "completed"}
        cols = st.columns(len(PIPELINE_STAGE_ORDER))
        for idx, stage in enumerate(PIPELINE_STAGE_ORDER):
            with cols[idx]:
                if stage in completed:
                    st.success(stage.value[:4])
                elif project.current_stage == stage:
                    st.warning(stage.value[:4])
                else:
                    st.info(stage.value[:4])

        st.subheader("Approval Gates")
        for gate in project.approval_gates:
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                label = f"{gate.stage.value} {'(required)' if gate.required else ''}"
                st.write(label)
            with c2:
                st.write("Approved" if gate.approved else "Pending")
            with c3:
                if gate.required and not gate.approved:
                    if st.button(f"Approve {gate.stage.value}", key=f"approve-{gate.stage.value}"):
                        orch.approve(project.id, gate.stage)
                        st.rerun()

        st.subheader("Run Stage")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            stage_to_run = st.selectbox("Stage", [s.value for s in PIPELINE_STAGE_ORDER])
        with rc2:
            through = st.selectbox("Run through (optional)", ["—"] + [s.value for s in PIPELINE_STAGE_ORDER])
        with rc3:
            auto_approve = st.checkbox("Auto-approve gates")

        if st.button("Run pipeline"):
            try:
                if through != "—":
                    orch.run_through(project.id, PipelineStage(through), auto_approve=auto_approve)
                else:
                    orch.run_stage(project.id, PipelineStage(stage_to_run))
                st.success("Stage completed")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        st.subheader("Health & Diagnosis")
        diagnosis = project.metadata.get("diagnosis", {})
        if diagnosis:
            metrics = diagnosis.get("metrics", {})
            m1, m2, m3 = st.columns(3)
            m1.metric("Services", diagnosis.get("service_count", 0))
            m2.metric("Smells", len(diagnosis.get("smells", [])))
            m3.metric("Graph density", f"{metrics.get('density', 0):.3f}")
            with st.expander("Smells"):
                st.json(diagnosis.get("smells", [])[:10])
        else:
            st.info("Run diagnose stage to see health metrics.")

        st.subheader("Hypotheses")
        hypotheses = project.metadata.get("hypotheses", [])
        if hypotheses:
            for hyp in hypotheses:
                with st.expander(f"{hyp.get('title')} ({hyp.get('confidence', 0):.0%})"):
                    st.write(hyp.get("description", ""))
                    st.caption(f"Target: {hyp.get('target_context')} | Source: {hyp.get('source', 'unknown')}")
        else:
            st.info("Run hypothesize stage to generate migration hypotheses.")

        st.subheader("Artifacts")
        artifact_index = project.metadata.get("artifact_index", {})
        if artifact_index:
            st.json(artifact_index)
        else:
            st.write("No artifacts saved yet.")

st.sidebar.header("API")
st.sidebar.code("uvicorn migrate_framework.api.main:app --reload --port 8080")
st.sidebar.header("CLI")
st.sidebar.code("migrate-framework init --name demo --source ../sample-bank")
