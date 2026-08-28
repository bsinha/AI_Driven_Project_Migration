"""Entity Framework Core adapter (registered stub)."""

from __future__ import annotations

from pathlib import Path

from migrate_framework.models import EvidenceItem, TechStackProfile


class EfCoreAdapter:
    name = "efcore"
    stacks = ["dotnet"]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        return profile.primary_stack() == "dotnet"

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        return []
