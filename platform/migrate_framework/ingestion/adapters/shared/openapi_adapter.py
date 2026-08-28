"""OpenAPI specification adapter."""

from __future__ import annotations

from pathlib import Path

import yaml

from migrate_framework.models import EvidenceItem, EvidenceRelation, TechStackProfile


class OpenApiAdapter:
    name = "openapi"
    stacks = ["*"]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        return bool(list(root.rglob("openapi.yaml")) + list(root.rglob("openapi.yml")))

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        for spec_path in sorted(set(root.rglob("openapi.yaml")) | set(root.rglob("openapi.yml"))):
            service_id = self._service_id(spec_path)
            try:
                spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue

            items.append(
                EvidenceItem(
                    type="service",
                    source=self.name,
                    subject=service_id,
                    attributes={
                        "spec_path": str(spec_path.relative_to(root)),
                        "title": (spec.get("info") or {}).get("title", service_id),
                        "version": (spec.get("info") or {}).get("version"),
                    },
                    tags=["api", "openapi"],
                )
            )

            for path, methods in (spec.get("paths") or {}).items():
                for method, operation in methods.items():
                    if method.startswith("x-"):
                        continue
                    if not isinstance(operation, dict):
                        continue
                    items.append(
                        EvidenceItem(
                            type="api_endpoint",
                            source=self.name,
                            subject=f"{service_id}:{method.upper()} {path}",
                            attributes={
                                "service": service_id,
                                "method": method.upper(),
                                "path": path,
                                "summary": operation.get("summary"),
                            },
                            relations=[EvidenceRelation(relation="exposes", target=service_id)],
                            tags=["api"],
                        )
                    )
        return items

    @staticmethod
    def _service_id(spec_path: Path) -> str:
        parent = spec_path.parent.name
        if parent in {"resources", "spec", "api"}:
            return spec_path.parent.parent.name
        return parent
