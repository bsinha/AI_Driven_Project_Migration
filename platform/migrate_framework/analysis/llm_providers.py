"""LLM provider abstraction and multi-model synthesis."""

from __future__ import annotations

import json
import os
from typing import Any

from migrate_framework.models import Landscape


def configured_providers() -> list[str]:
    providers: list[str] = []
    if os.getenv("OPENAI_API_KEY", "").strip():
        providers.append("openai")
    if os.getenv("AZURE_OPENAI_API_KEY", "").strip() or os.getenv("AZURE_OPENAI_ENDPOINT", "").strip():
        providers.append("azure")
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        providers.append("anthropic")
    return providers


def run_hypothesis_prompt(
    provider: str,
    diagnosis: dict[str, Any],
    landscape: Landscape | None,
) -> list[dict[str, Any]]:
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
    messages = [
        {"role": "system", "content": "Respond with valid JSON only — an array of hypothesis objects."},
        {"role": "user", "content": prompt},
    ]

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        content = response.choices[0].message.content or "[]"
    elif provider == "azure":
        from openai import AzureOpenAI

        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )
        model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
        response = client.chat.completions.create(model=model, messages=messages, temperature=0.2)
        content = response.choices[0].message.content or "[]"
    elif provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=messages[0]["content"],
            messages=[{"role": "user", "content": messages[1]["content"]}],
            temperature=0.2,
        )
        content = response.content[0].text if response.content else "[]"
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
    hypotheses = json.loads(content)
    if not isinstance(hypotheses, list):
        raise ValueError(f"Provider {provider} response was not a JSON array")
    return hypotheses


def run_multi_provider_hypotheses(
    diagnosis: dict[str, Any],
    landscape: Landscape | None,
    providers: list[str] | None = None,
) -> dict[str, Any]:
    """Run hypothesis generation across providers; store per-provider results."""
    active = providers or configured_providers()
    results: dict[str, list[dict[str, Any]]] = {}
    errors: dict[str, str] = {}

    for provider in active:
        try:
            results[provider] = run_hypothesis_prompt(provider, diagnosis, landscape)
        except Exception as exc:
            errors[provider] = str(exc)

    synthesized = synthesize_hypotheses(results)
    return {
        "by_provider": results,
        "errors": errors,
        "synthesized": synthesized,
        "providers_used": list(results.keys()),
        "consensus": synthesized.get("consensus", False),
    }


def synthesize_hypotheses(by_provider: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Merge multi-LLM outputs; flag disagreement when contexts diverge."""
    if not by_provider:
        return {"hypotheses": [], "consensus": True, "dissent_notes": []}

    if len(by_provider) == 1:
        hyps = next(iter(by_provider.values()))
        return {"hypotheses": hyps, "consensus": True, "dissent_notes": []}

    context_sets: dict[str, set[str]] = {}
    for provider, hyps in by_provider.items():
        contexts = {str(h.get("target_context", "")).lower() for h in hyps}
        context_sets[provider] = contexts

    all_contexts = set().union(*context_sets.values())
    consensus = all(context_sets[p] == all_contexts for p in context_sets)

    dissent_notes: list[str] = []
    if not consensus:
        for provider, contexts in context_sets.items():
            dissent_notes.append(f"{provider}: {', '.join(sorted(contexts)) or 'none'}")

    # Prefer highest-confidence hypothesis per target_context across providers
    merged: dict[str, dict[str, Any]] = {}
    for hyps in by_provider.values():
        for hyp in hyps:
            key = str(hyp.get("target_context", hyp.get("title", ""))).lower()
            if key not in merged or hyp.get("confidence", 0) > merged[key].get("confidence", 0):
                merged[key] = hyp

    return {
        "hypotheses": list(merged.values()),
        "consensus": consensus,
        "dissent_notes": dissent_notes,
    }
