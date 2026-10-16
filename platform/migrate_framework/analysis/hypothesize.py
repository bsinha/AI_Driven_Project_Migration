"""Migration hypothesis generation with optional OpenAI integration."""

from __future__ import annotations

import json
import os
from typing import Any

from migrate_framework.models import EvidenceItem, Landscape, new_id


def hypothesize(
    diagnosis: dict[str, Any],
    landscape: Landscape | None,
    evidence: list[EvidenceItem] | None = None,
) -> list[dict[str, Any]]:
    """Generate migration hypotheses using configured LLM(s) or deterministic mock fallback."""
    _ = evidence
    use_multi = os.getenv("MULTI_LLM", "").lower() in {"1", "true", "yes"}
    if use_multi:
        from migrate_framework.analysis.llm_providers import configured_providers, run_multi_provider_hypotheses

        providers = configured_providers()
        if providers:
            try:
                multi = run_multi_provider_hypotheses(diagnosis, landscape, providers)
                hyps = multi.get("synthesized", {}).get("hypotheses", [])
                return [_normalize_hypothesis(h) for h in hyps]
            except Exception as exc:
                return _mock_hypotheses(diagnosis, landscape, fallback_reason=str(exc))

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        try:
            return _openai_hypotheses(diagnosis, landscape, api_key)
        except Exception as exc:
            return _mock_hypotheses(diagnosis, landscape, fallback_reason=str(exc))
    return _mock_hypotheses(diagnosis, landscape)


def _openai_hypotheses(
    diagnosis: dict[str, Any],
    landscape: Landscape | None,
    api_key: str,
) -> list[dict[str, Any]]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    context_summary = {
        "diagnosis": {
            "smells": diagnosis.get("smells", [])[:10],
            "database_sharing": diagnosis.get("database_sharing", {}),
            "cohesion": diagnosis.get("cohesion", {}),
        },
        "target_bounded_contexts": [
            {"name": c.name, "services": c.services}
            for c in (landscape.target_bounded_contexts if landscape else [])
        ],
    }

    prompt = (
        "You are a microservices-to-DDD migration architect. "
        "Given the diagnosis JSON, produce 3-5 migration hypotheses as a JSON array. "
        "Each item must have: id, title, description, target_context, confidence (0-1), "
        "rationale, affected_services (array).\n\n"
        f"Context:\n{json.dumps(context_summary, indent=2)}"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Respond with valid JSON only — an array of hypothesis objects."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content or "[]"
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
    hypotheses = json.loads(content)
    if not isinstance(hypotheses, list):
        raise ValueError("OpenAI response was not a JSON array")
    return [_normalize_hypothesis(h) for h in hypotheses]


def _mock_hypotheses(
    diagnosis: dict[str, Any],
    landscape: Landscape | None,
    fallback_reason: str | None = None,
) -> list[dict[str, Any]]:
    """Deterministic hypotheses based on target_bounded_contexts."""
    hypotheses: list[dict[str, Any]] = []

    if landscape and landscape.target_bounded_contexts:
        for ctx in landscape.target_bounded_contexts:
            shared_dbs = [
                db for db, svcs in diagnosis.get("database_sharing", {}).items()
                if any(s in ctx.services for s in svcs)
            ]
            hypotheses.append(
                {
                    "id": new_id("hyp"),
                    "title": f"Consolidate into '{ctx.name}' bounded context",
                    "description": (
                        f"Merge {len(ctx.services)} services ({', '.join(ctx.services[:3])}"
                        f"{'...' if len(ctx.services) > 3 else ''}) into a single "
                        f"{ctx.name} deployable with modular monolith or well-bounded microservices."
                    ),
                    "target_context": ctx.name,
                    "confidence": 0.85 if shared_dbs else 0.75,
                    "rationale": (
                        f"Landscape manifest defines {ctx.name} as target context with "
                        f"{len(ctx.services)} candidate services."
                        + (f" Shared databases detected: {', '.join(shared_dbs)}." if shared_dbs else "")
                    ),
                    "affected_services": ctx.services,
                    "source": "mock",
                }
            )

    smells = diagnosis.get("smells", [])
    if any(s.get("type") == "sync_rest_chain" for s in smells):
        hypotheses.append(
            {
                "id": new_id("hyp"),
                "title": "Introduce async integration for payment chain",
                "description": "Replace synchronous REST chains in payment flow with outbox/events.",
                "target_context": "Payments",
                "confidence": 0.8,
                "rationale": "Diagnosis detected sync REST chains in payment domain.",
                "affected_services": [
                    s for s in (landscape.services if landscape else [])
                    if "payment" in getattr(s, "id", str(s))
                ] if landscape else [],
                "source": "mock",
            }
        )

    if not hypotheses:
        hypotheses.append(
            {
                "id": new_id("hyp"),
                "title": "Baseline strangler-fig migration",
                "description": "Incrementally extract bounded contexts behind an API gateway.",
                "target_context": "General",
                "confidence": 0.6,
                "rationale": "Default hypothesis when no landscape contexts are defined.",
                "affected_services": [],
                "source": "mock",
            }
        )

    if fallback_reason:
        for h in hypotheses:
            h["fallback_reason"] = fallback_reason

    return hypotheses


def _normalize_hypothesis(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw.get("id") or new_id("hyp"),
        "title": raw.get("title", "Untitled hypothesis"),
        "description": raw.get("description", ""),
        "target_context": raw.get("target_context", "General"),
        "confidence": float(raw.get("confidence", 0.7)),
        "rationale": raw.get("rationale", ""),
        "affected_services": raw.get("affected_services") or [],
        "source": "openai",
    }


def hypotheses_to_evidence(hypotheses: list[dict[str, Any]]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            type="migration_hypothesis",
            source="hypothesize",
            subject=h["title"],
            confidence=h.get("confidence", 0.7),
            attributes=h,
            tags=["hypothesis", h.get("target_context", "")],
        )
        for h in hypotheses
    ]
