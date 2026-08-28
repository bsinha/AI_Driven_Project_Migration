"""Landscape manifest metadata adapter."""

from __future__ import annotations

from pathlib import Path

import yaml

from migrate_framework.models import (
    BoundedContextTarget,
    EvidenceItem,
    EvidenceRelation,
    Landscape,
    LandscapeService,
    TechStackProfile,
)


class MetadataAdapter:
    name = "metadata"
    stacks = ["*"]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        return self._find_manifest(root) is not None

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        manifest_path = self._find_manifest(root)
        if manifest_path is None:
            return []

        try:
            doc = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return []

        items: list[EvidenceItem] = []
        bank = doc.get("bank") or {}
        for svc in doc.get("services") or []:
            if not isinstance(svc, dict) or "id" not in svc:
                continue
            svc_id = svc["id"]
            relations = [
                EvidenceRelation(relation="depends_on", target=dep)
                for dep in svc.get("depends_on") or []
            ]
            items.append(
                EvidenceItem(
                    type="service",
                    source=self.name,
                    subject=svc_id,
                    attributes={
                        "port": svc.get("port"),
                        "database": svc.get("database"),
                        "tables": svc.get("tables") or [],
                        "team": svc.get("team"),
                        "region_notes": svc.get("region_notes"),
                        "manifest_path": str(manifest_path.relative_to(root)),
                    },
                    relations=relations,
                    tags=["landscape", "manifest"],
                )
            )

            for smell in svc.get("smells") or []:
                items.append(
                    EvidenceItem(
                        type="landscape_smell",
                        source=self.name,
                        subject=f"{svc_id}:{smell}",
                        attributes={"service": svc_id, "smell": smell},
                        relations=[EvidenceRelation(relation="belongs_to", target=svc_id)],
                        tags=["smell"],
                    )
                )

            if svc.get("team"):
                items.append(
                    EvidenceItem(
                        type="team_ownership",
                        source=self.name,
                        subject=f"{svc_id}:{svc['team']}",
                        attributes={"service": svc_id, "team": svc["team"]},
                        relations=[EvidenceRelation(relation="owns", target=svc_id)],
                    )
                )

            db_name = svc.get("database")
            if db_name:
                items.append(
                    EvidenceItem(
                        type="database",
                        source=self.name,
                        subject=db_name,
                        attributes={"shared_by_service": svc_id},
                        tags=["database"],
                    )
                )
                for table in svc.get("tables") or []:
                    items.append(
                        EvidenceItem(
                            type="database_table",
                            source=self.name,
                            subject=f"{db_name}.{table}",
                            attributes={"database": db_name, "table": table, "service": svc_id},
                            relations=[
                                EvidenceRelation(relation="stores_in", target=db_name),
                                EvidenceRelation(relation="belongs_to", target=svc_id),
                            ],
                            tags=["database"],
                        )
                    )

            for dep in svc.get("depends_on") or []:
                items.append(
                    EvidenceItem(
                        type="http_dependency",
                        source=self.name,
                        subject=f"{svc_id}->{dep}",
                        attributes={"from": svc_id, "to": dep, "via": "landscape-manifest"},
                        relations=[
                            EvidenceRelation(relation="depends_on", target=dep),
                            EvidenceRelation(relation="calls", target=dep),
                        ],
                        tags=["dependency"],
                    )
                )

        for ctx in doc.get("target_bounded_contexts") or []:
            if not isinstance(ctx, dict):
                continue
            ctx_name = ctx.get("name", "Unknown")
            items.append(
                EvidenceItem(
                    type="bounded_context",
                    source=self.name,
                    subject=ctx_name,
                    attributes={
                        "services": ctx.get("services") or [],
                        "bank": bank.get("name"),
                    },
                    relations=[
                        EvidenceRelation(relation="targets", target=s)
                        for s in ctx.get("services") or []
                    ],
                    tags=["target", "ddd"],
                )
            )

        return items

    @staticmethod
    def load_landscape(root: Path) -> Landscape | None:
        manifest_path = MetadataAdapter._find_manifest(root)
        if manifest_path is None:
            return None
        doc = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        bank = doc.get("bank") or {}
        services = [
            LandscapeService(
                id=s["id"],
                port=s.get("port"),
                database=s.get("database"),
                tables=s.get("tables") or [],
                depends_on=s.get("depends_on") or [],
                team=s.get("team"),
                smells=s.get("smells") or [],
                region_notes=s.get("region_notes"),
            )
            for s in doc.get("services") or []
            if isinstance(s, dict) and "id" in s
        ]
        contexts = [
            BoundedContextTarget(name=c.get("name", ""), services=c.get("services") or [])
            for c in doc.get("target_bounded_contexts") or []
            if isinstance(c, dict)
        ]
        return Landscape(
            name=bank.get("name", "Unknown"),
            regions=bank.get("regions") or [],
            currencies=bank.get("currencies") or [],
            services=services,
            target_bounded_contexts=contexts,
            source_path=str(manifest_path),
        )

    @staticmethod
    def _find_manifest(root: Path) -> Path | None:
        candidates = [
            root / "landscape-manifest.yaml",
            root / "landscape-manifest.yml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        for candidate in root.rglob("landscape-manifest.yaml"):
            return candidate
        for candidate in root.rglob("landscape-manifest.yml"):
            return candidate
        return None
