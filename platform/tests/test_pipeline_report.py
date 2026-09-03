"""Tests for pipeline report generation."""

from migrate_framework.branding import PRODUCT_NAME
from migrate_framework.models import MigrationProject, PipelineStage, StageRun
from migrate_framework.reporting.pipeline_report import (
    generate_html_report,
    generate_markdown_report,
    report_filename,
)


def test_generate_markdown_report_includes_core_sections() -> None:
    project = MigrationProject(
        id="proj-test123",
        name="EuroSA Bank Migration",
        source_root="/sample-bank",
        current_stage=PipelineStage.PLAN,
        stage_runs=[
            StageRun(stage=PipelineStage.DISCOVER, status="completed"),
            StageRun(stage=PipelineStage.DIAGNOSE, status="completed"),
        ],
        metadata={
            "diagnosis": {
                "service_count": 16,
                "smells": [
                    {
                        "type": "shared_database",
                        "severity": "high",
                        "subject": "customer_db",
                        "services": ["customer-identity-service", "customer-address-service"],
                    }
                ],
                "metrics": {"density": 0.01},
                "coupling": {"sync_chains": []},
                "recommendations_preview": ["Consolidate shared databases."],
            },
            "hypotheses": [
                {
                    "title": "Consolidate Customer Management",
                    "description": "Merge customer services.",
                    "target_context": "Customer Management",
                    "confidence": 0.85,
                    "affected_services": ["customer-identity-service"],
                }
            ],
        },
    )

    report = generate_markdown_report(project)

    assert "# Migration Assessment Report: EuroSA Bank Migration" in report
    assert "## Executive Summary" in report
    assert "## Pipeline Status" in report
    assert "## Architecture Health" in report
    assert "customer-identity-service" in report
    assert "## Migration Hypotheses" in report
    assert PRODUCT_NAME in report
    assert report_filename(project, "md").endswith(".md")


def test_generate_html_report_is_html_document() -> None:
    project = MigrationProject(
        id="proj-test123",
        name="Demo",
        source_root="/sample-bank",
    )
    html_report = generate_html_report(project)
    assert html_report.startswith("<!DOCTYPE html>")
    assert PRODUCT_NAME in html_report
    assert "Demo" in html_report
    assert "background-color: #ffffff" in html_report
    assert 'color-scheme: light' in html_report

    embed_report = generate_html_report(project, embed=True)
    assert "background-color: #ffffff !important" in embed_report
