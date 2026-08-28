"""Spring Boot Java adapter."""

from __future__ import annotations

import re
from pathlib import Path

from migrate_framework.models import EvidenceItem, EvidenceRelation, TechStackProfile

SPRING_BOOT_APP_RE = re.compile(
    r"@SpringBootApplication|SpringApplication\.run\s*\(",
    re.MULTILINE,
)


class SpringBootAdapter:
    name = "spring-boot"
    stacks = ["java", "java-spring"]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        return "spring-boot" in profile.frameworks or bool(list(root.rglob("*Application.java")))

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        for java_path in sorted(root.rglob("*Application.java")):
            try:
                content = java_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if not SPRING_BOOT_APP_RE.search(content):
                continue

            service_id = self._service_id(java_path, content)
            items.append(
                EvidenceItem(
                    type="framework",
                    source=self.name,
                    subject=service_id,
                    attributes={
                        "framework": "spring-boot",
                        "entrypoint": str(java_path.relative_to(root)),
                        "language": "java",
                    },
                    relations=[EvidenceRelation(relation="belongs_to", target=service_id)],
                    tags=["java", "spring-boot"],
                )
            )
            items.append(
                EvidenceItem(
                    type="service",
                    source=self.name,
                    subject=service_id,
                    attributes={"runtime": "spring-boot", "entrypoint": java_path.name},
                    tags=["java", "service"],
                )
            )
        profile.frameworks.append("spring-boot")
        profile.languages.append("java")
        return items

    @staticmethod
    def _service_id(java_path: Path, content: str) -> str:
        parts = java_path.parts
        if "granular-services" in parts:
            idx = parts.index("granular-services")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        match = re.search(r"artifactId[>(\s]+([a-z0-9-]+)", content, re.IGNORECASE)
        if match:
            return match.group(1)
        return java_path.parent.parent.parent.name
