"""Csproj adapter (registered stub)."""

from __future__ import annotations

from pathlib import Path

from migrate_framework.models import EvidenceItem, TechStackProfile


class CsprojAdapter:
    name = "csproj"
    stacks = ["dotnet"]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        return bool(list(root.rglob("*.csproj")))

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        return []
