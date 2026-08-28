"""Distributed trace / call-chain adapter (heuristic from application.yml)."""

from __future__ import annotations

from pathlib import Path

import yaml

from migrate_framework.models import EvidenceItem, EvidenceRelation, TechStackProfile


class TraceAdapter:
    name = "trace"
    stacks = ["*"]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        return bool(list(root.rglob("application.yml")) + list(root.rglob("application.yaml")))

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        config_files = sorted(
            set(root.rglob("application.yml")) | set(root.rglob("application.yaml"))
        )
        for cfg_path in config_files:
            service_id = self._service_id(cfg_path)
            try:
                doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue

            downstream = (
                (doc.get("eurosa") or {}).get("downstream")
                or (doc.get("bank") or {}).get("downstream")
                or {}
            )
            if isinstance(downstream, dict):
                for target, url in downstream.items():
                    items.append(
                        EvidenceItem(
                            type="trace_span",
                            source=self.name,
                            subject=f"{service_id}->{target}",
                            attributes={
                                "from": service_id,
                                "to": target,
                                "url": url,
                                "config_path": str(cfg_path.relative_to(root)),
                            },
                            relations=[
                                EvidenceRelation(relation="calls", target=str(target)),
                            ],
                            tags=["trace", "runtime"],
                        )
                    )
                    items.append(
                        EvidenceItem(
                            type="http_dependency",
                            source=self.name,
                            subject=f"{service_id}->{target}",
                            attributes={"from": service_id, "to": target, "via": "application.yml"},
                            relations=[EvidenceRelation(relation="calls", target=str(target))],
                            tags=["dependency"],
                        )
                    )

            spring_name = ((doc.get("spring") or {}).get("application") or {}).get("name")
            if spring_name:
                items.append(
                    EvidenceItem(
                        type="config_property",
                        source=self.name,
                        subject=f"{service_id}:spring.application.name",
                        attributes={"service": service_id, "value": spring_name},
                        relations=[EvidenceRelation(relation="belongs_to", target=service_id)],
                    )
                )
        return items

    @staticmethod
    def _service_id(cfg_path: Path) -> str:
        parts = cfg_path.parts
        if "granular-services" in parts:
            idx = parts.index("granular-services")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        spring_name = None
        try:
            doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            spring_name = ((doc.get("spring") or {}).get("application") or {}).get("name")
        except (OSError, yaml.YAMLError):
            pass
        return spring_name or cfg_path.parents[2].name if len(cfg_path.parents) > 2 else "unknown"
