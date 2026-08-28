"""Maven POM adapter."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from migrate_framework.models import EvidenceItem, EvidenceRelation, TechStackProfile

NS = {"m": "http://maven.apache.org/POM/4.0.0"}


class MavenAdapter:
    name = "maven"
    stacks = ["java", "java-spring"]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        return bool(list(root.rglob("pom.xml")))

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        spring_boot_detected = False

        for pom_path in sorted(root.rglob("pom.xml")):
            try:
                tree = ET.parse(pom_path)
                root_el = tree.getroot()
            except (OSError, ET.ParseError):
                continue

            artifact = self._text(root_el, "m:artifactId") or pom_path.parent.name
            group = self._text(root_el, "m:groupId")
            version = self._text(root_el, "m:version")
            java_version = self._text(root_el, ".//m:properties/m:java.version")

            deps = []
            for dep in root_el.findall(".//m:dependency", NS):
                artifact_id = self._text(dep, "m:artifactId")
                if artifact_id:
                    deps.append(artifact_id)
                    if artifact_id == "spring-boot-starter-parent" or "spring-boot" in artifact_id:
                        spring_boot_detected = True

            parent = root_el.find("m:parent", NS)
            if parent is not None:
                parent_art = self._text(parent, "m:artifactId")
                if parent_art and "spring-boot" in parent_art:
                    spring_boot_detected = True

            items.append(
                EvidenceItem(
                    type="build_artifact",
                    source=self.name,
                    subject=artifact,
                    attributes={
                        "group_id": group,
                        "artifact_id": artifact,
                        "version": version,
                        "java_version": java_version,
                        "dependencies": deps,
                        "pom_path": str(pom_path.relative_to(root)),
                    },
                    relations=[EvidenceRelation(relation="belongs_to", target=artifact)],
                    tags=["maven", "build"],
                )
            )

        if spring_boot_detected and "spring-boot" not in profile.frameworks:
            profile.frameworks.append("spring-boot")
        if "java" not in profile.languages:
            profile.languages.append("java")
        if "maven" not in profile.build_tools:
            profile.build_tools.append("maven")
        return items

    @staticmethod
    def _text(el: ET.Element, path: str) -> str | None:
        if path.startswith(".//"):
            found = el.find(path, NS)
        else:
            found = el.find(path, NS)
        if found is not None and found.text:
            return found.text.strip()
        return None
