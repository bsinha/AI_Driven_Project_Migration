"""Tests for adapter registry and stack detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from migrate_framework.ingestion.registry import AdapterRegistry, detect_stack


@pytest.fixture
def dotnet_repo(tmp_path: Path) -> Path:
    svc = tmp_path / "PaymentService"
    svc.mkdir()
    (svc / "PaymentService.csproj").write_text(
        """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.AspNetCore.App" />
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="8.0.0" />
  </ItemGroup>
</Project>
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def java_repo(tmp_path: Path) -> Path:
    svc = tmp_path / "customer-service"
    svc.mkdir()
    (svc / "pom.xml").write_text(
        """<project>
  <parent>
    <artifactId>spring-boot-starter-parent</artifactId>
  </parent>
  <artifactId>customer-service</artifactId>
</project>
""",
        encoding="utf-8",
    )
    return tmp_path


def test_detect_stack_dotnet(dotnet_repo: Path) -> None:
    profile = detect_stack(dotnet_repo)
    assert profile.primary_stack() == "dotnet"
    assert "csharp" in profile.languages
    assert "aspnetcore" in profile.frameworks


def test_adapters_for_dotnet_includes_stubs(dotnet_repo: Path) -> None:
    registry = AdapterRegistry()
    profile = detect_stack(dotnet_repo)
    adapters = registry.adapters_for(dotnet_repo, profile)
    names = {a.name for a in adapters}
    assert "csproj" in names
    assert "aspnetcore" in names
    assert "efcore" in names


def test_dotnet_adapters_return_empty_but_registered(dotnet_repo: Path) -> None:
    registry = AdapterRegistry()
    profile = detect_stack(dotnet_repo)
    evidence, _ = registry.collect_all(dotnet_repo, profile)
    dotnet_adapter_names = {"csproj", "aspnetcore", "efcore"}
    selected = {a.name for a in registry.adapters_for(dotnet_repo, profile)}
    assert dotnet_adapter_names.issubset(selected)
    assert evidence == []


def test_java_stack_selects_maven_not_dotnet(java_repo: Path) -> None:
    registry = AdapterRegistry()
    profile = detect_stack(java_repo)
    assert profile.primary_stack() in {"java", "java-spring"}
    adapters = registry.adapters_for(java_repo, profile)
    names = {a.name for a in adapters}
    assert "maven" in names
    assert "csproj" not in names
