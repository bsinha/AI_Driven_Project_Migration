#!/usr/bin/env python3
"""Generate granular Spring Boot service modules from landscape-manifest.yaml."""

from __future__ import annotations

import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sample-bank" / "landscape-manifest.yaml"
SERVICES_DIR = ROOT / "sample-bank" / "granular-services"

POM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.3.4</version>
        <relativePath/>
    </parent>
    <groupId>com.eurosa.bank</groupId>
    <artifactId>{artifact_id}</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>{artifact_id}</name>
    <properties>
        <java.version>17</java.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>com.mysql</groupId>
            <artifactId>mysql-connector-j</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
"""

APPLICATION_YML = """server:
  port: {port}

spring:
  application:
    name: {service_id}
  datasource:
    url: jdbc:mysql://localhost:3306/{database}?createDatabaseIfNotExist=true&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC
    username: ${{DB_USERNAME:root}}
    password: ${{DB_PASSWORD:root}}
  jpa:
    hibernate:
      ddl-auto: update

eurosa:
  downstream:
{downstream_yaml}
"""

OPENAPI = """openapi: 3.0.3
info:
  title: {service_id}
  version: 1.0.0
paths:
  /api/health:
    get:
      summary: Health check
      responses:
        '200':
          description: OK
  /api/{resource}:
    get:
      summary: List {resource}
      responses:
        '200':
          description: OK
    post:
      summary: Create {resource}
      responses:
        '201':
          description: Created
"""


def pkg_name(service_id: str) -> str:
    return service_id.replace("-", "")


def main() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    for svc in data["services"]:
        sid = svc["id"]
        port = svc["port"]
        db = svc["database"]
        deps = svc.get("depends_on", [])
        resource = sid.replace("-service", "").replace("-", "_")

        base = SERVICES_DIR / sid
        java_pkg = f"com/eurosa/bank/{pkg_name(sid)}"
        java_dir = base / "src" / "main" / "java" / Path(*java_pkg.split("/"))
        res_dir = base / "src" / "main" / "resources"
        java_dir.mkdir(parents=True, exist_ok=True)
        res_dir.mkdir(parents=True, exist_ok=True)

        (base / "pom.xml").write_text(POM_TEMPLATE.format(artifact_id=sid), encoding="utf-8")
        dep_ports = {s["id"]: s["port"] for s in data["services"]}
        downstream = "\n".join(
            f"    {d}: http://localhost:{dep_ports[d]}" for d in deps if d in dep_ports
        )
        if not downstream:
            downstream = "    {}"
        (res_dir / "application.yml").write_text(
            APPLICATION_YML.format(port=port, service_id=sid, database=db, downstream_yaml=downstream or "    {}"),
            encoding="utf-8",
        )
        (base / "openapi.yaml").write_text(OPENAPI.format(service_id=sid, resource=resource), encoding="utf-8")

        app_class = "ServiceApplication"
        ctrl_class = "ServiceController"
        pkg = f"com.eurosa.bank.{pkg_name(sid)}"

        java_dir.mkdir(parents=True, exist_ok=True)
        (java_dir / f"{app_class}.java").write_text(
            textwrap.dedent(
                f"""
                package {pkg};

                import org.springframework.boot.SpringApplication;
                import org.springframework.boot.autoconfigure.SpringBootApplication;

                @SpringBootApplication
                public class {app_class} {{
                    public static void main(String[] args) {{
                        SpringApplication.run({app_class}.class, args);
                    }}
                }}
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        (java_dir / f"{ctrl_class}.java").write_text(
            textwrap.dedent(
                f"""
                package {pkg};

                import org.springframework.web.bind.annotation.*;
                import java.util.List;
                import java.util.Map;

                @RestController
                @RequestMapping("/api")
                public class {ctrl_class} {{

                    @GetMapping("/health")
                    public Map<String, String> health() {{
                        return Map.of("service", "{sid}", "status", "UP");
                    }}

                    @GetMapping("/{resource}")
                    public List<Map<String, Object>> list() {{
                        return List.of(Map.of("service", "{sid}"));
                    }}

                    @PostMapping("/{resource}")
                    public Map<String, Object> create(@RequestBody Map<String, Object> body) {{
                        return Map.of("service", "{sid}", "created", true);
                    }}
                }}
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        table = svc["tables"][0]
        entity = "".join(p.capitalize() for p in table.split("_"))
        if entity.endswith("s"):
            entity = entity[:-1]
        (java_dir / f"{entity}.java").write_text(
            textwrap.dedent(
                f"""
                package {pkg};

                import jakarta.persistence.*;
                import lombok.*;

                @Entity
                @Table(name = "{table}")
                @Data
                @NoArgsConstructor
                @AllArgsConstructor
                public class {entity} {{
                    @Id
                    @GeneratedValue(strategy = GenerationType.IDENTITY)
                    private Long id;
                    private String name;
                }}
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        flyway = res_dir / "db" / "migration"
        flyway.mkdir(parents=True, exist_ok=True)
        (flyway / "V1__init.sql").write_text(
            f"CREATE TABLE IF NOT EXISTS {table} (id BIGINT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255));\n",
            encoding="utf-8",
        )

    print(f"Generated {len(data['services'])} granular services in {SERVICES_DIR}")


if __name__ == "__main__":
    main()
