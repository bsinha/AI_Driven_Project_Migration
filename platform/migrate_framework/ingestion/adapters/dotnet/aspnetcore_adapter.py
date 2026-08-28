"""ASP.NET Core adapter (registered stub)."""

from __future__ import annotations

from pathlib import Path

from migrate_framework.models import EvidenceItem, TechStackProfile


class AspNetCoreAdapter:
    name = "aspnetcore"
    stacks = ["dotnet"]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        return profile.primary_stack() == "dotnet" or bool(list(root.rglob("*.csproj")))

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        return []
