"""Base protocol for evidence ingestion adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from migrate_framework.models import EvidenceItem, TechStackProfile


@runtime_checkable
class IngestionAdapter(Protocol):
    """Collect structured evidence from a source repository."""

    name: str
    stacks: list[str]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        """Return True when this adapter should run for the given repo profile."""

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        """Collect evidence items from the repository."""
