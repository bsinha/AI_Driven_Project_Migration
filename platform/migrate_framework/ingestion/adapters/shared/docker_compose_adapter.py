"""Docker Compose deployment adapter."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from migrate_framework.models import EvidenceItem, EvidenceRelation, TechStackProfile


class DockerComposeAdapter:
    name = "docker-compose"
    stacks = ["*"]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        return bool(list(root.glob("docker-compose*.yml")) + list(root.glob("docker-compose*.yaml")))

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        compose_files = sorted(
            set(root.glob("docker-compose*.yml")) | set(root.glob("docker-compose*.yaml"))
        )
        for compose_path in compose_files:
            try:
                doc = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue

            services = doc.get("services") or {}
            for svc_name, svc_def in services.items():
                if not isinstance(svc_def, dict):
                    continue
                depends_on = svc_def.get("depends_on") or []
                if isinstance(depends_on, dict):
                    depends_on = list(depends_on.keys())

                relations = [
                    EvidenceRelation(relation="depends_on", target=str(dep))
                    for dep in depends_on
                ]
                items.append(
                    EvidenceItem(
                        type="deployment_unit",
                        source=self.name,
                        subject=svc_name,
                        attributes={
                            "compose_file": str(compose_path.relative_to(root)),
                            "image": svc_def.get("image"),
                            "ports": svc_def.get("ports"),
                            "environment_keys": list((svc_def.get("environment") or {}).keys())
                            if isinstance(svc_def.get("environment"), dict)
                            else [],
                        },
                        relations=relations,
                        tags=["deployment", "docker"],
                    )
                )

                for dep in depends_on:
                    items.append(
                        EvidenceItem(
                            type="http_dependency",
                            source=self.name,
                            subject=f"{svc_name}->{dep}",
                            attributes={"from": svc_name, "to": dep, "via": "docker-compose"},
                            relations=[
                                EvidenceRelation(relation="depends_on", target=str(dep)),
                                EvidenceRelation(relation="calls", target=str(dep)),
                            ],
                            tags=["dependency"],
                        )
                    )

            profile.deployment.append("docker-compose")
        return items
