"""Stack detection and adapter registry."""

from __future__ import annotations

from pathlib import Path

from migrate_framework.ingestion.adapters.base import IngestionAdapter
from migrate_framework.ingestion.adapters.dotnet.aspnetcore_adapter import AspNetCoreAdapter
from migrate_framework.ingestion.adapters.dotnet.csproj_adapter import CsprojAdapter
from migrate_framework.ingestion.adapters.dotnet.efcore_adapter import EfCoreAdapter
from migrate_framework.ingestion.adapters.java.maven_adapter import MavenAdapter
from migrate_framework.ingestion.adapters.java.spring_boot_adapter import SpringBootAdapter
from migrate_framework.ingestion.adapters.shared.docker_compose_adapter import DockerComposeAdapter
from migrate_framework.ingestion.adapters.shared.metadata_adapter import MetadataAdapter
from migrate_framework.ingestion.adapters.shared.openapi_adapter import OpenApiAdapter
from migrate_framework.ingestion.adapters.shared.sql_migration_adapter import SqlMigrationAdapter
from migrate_framework.ingestion.adapters.shared.trace_adapter import TraceAdapter
from migrate_framework.models import TechStackProfile


def detect_stack(root: Path) -> TechStackProfile:
    """Inspect repository files to build a tech stack profile."""
    profile = TechStackProfile()
    root = root.resolve()

    pom_files = list(root.rglob("pom.xml"))
    csproj_files = list(root.rglob("*.csproj"))
    compose_files = list(root.glob("docker-compose*.yml")) + list(root.glob("docker-compose*.yaml"))

    for pom in pom_files[:20]:
        profile.detected_files.append(str(pom.relative_to(root)))
        try:
            text = pom.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "spring-boot" in text:
            if "spring-boot" not in profile.frameworks:
                profile.frameworks.append("spring-boot")
        if "java" not in profile.languages:
            profile.languages.append("java")
        if "maven" not in profile.build_tools:
            profile.build_tools.append("maven")

    for csproj in csproj_files[:20]:
        profile.detected_files.append(str(csproj.relative_to(root)))
        if "csharp" not in profile.languages:
            profile.languages.append("csharp")
        if "dotnet" not in profile.languages:
            profile.languages.append("dotnet")
        try:
            text = csproj.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "Microsoft.AspNetCore" in text or "Sdk=\"Microsoft.NET.Sdk.Web\"" in text:
            if "aspnetcore" not in profile.frameworks:
                profile.frameworks.append("aspnetcore")
        if "Microsoft.EntityFrameworkCore" in text:
            if "efcore" not in profile.frameworks:
                profile.frameworks.append("efcore")

    for compose in compose_files:
        profile.detected_files.append(str(compose.relative_to(root)))
        if "docker-compose" not in profile.deployment:
            profile.deployment.append("docker-compose")

    if root.rglob("**/db/migration/*.sql"):
        if "flyway-style-sql" not in profile.databases:
            profile.databases.append("flyway-style-sql")

    return profile


class AdapterRegistry:
    """Registry of all ingestion adapters."""

    def __init__(self) -> None:
        self._adapters: list[IngestionAdapter] = [
            MetadataAdapter(),
            OpenApiAdapter(),
            DockerComposeAdapter(),
            SqlMigrationAdapter(),
            TraceAdapter(),
            MavenAdapter(),
            SpringBootAdapter(),
            AspNetCoreAdapter(),
            CsprojAdapter(),
            EfCoreAdapter(),
        ]

    @property
    def adapters(self) -> list[IngestionAdapter]:
        return list(self._adapters)

    def adapters_for(self, root: Path, profile: TechStackProfile | None = None) -> list[IngestionAdapter]:
        """Return adapters applicable to the repository stack."""
        if profile is None:
            profile = detect_stack(root)
        stack = profile.primary_stack()
        selected: list[IngestionAdapter] = []

        for adapter in self._adapters:
            stacks = getattr(adapter, "stacks", ["*"])
            if "*" in stacks or stack in stacks or any(s in stacks for s in profile.languages):
                if adapter.can_handle(root, profile):
                    selected.append(adapter)
        return selected

    def collect_all(self, root: Path, profile: TechStackProfile | None = None) -> tuple[list, TechStackProfile]:
        if profile is None:
            profile = detect_stack(root)
        evidence = []
        for adapter in self.adapters_for(root, profile):
            evidence.extend(adapter.collect(root, profile))
        return evidence, profile


DEFAULT_REGISTRY = AdapterRegistry()
