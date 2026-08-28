"""SQL migration (Flyway/Liquibase-style) adapter."""

from __future__ import annotations

import re
from pathlib import Path

from migrate_framework.models import EvidenceItem, EvidenceRelation, TechStackProfile

CREATE_TABLE_RE = re.compile(
    r"create\s+table\s+(?:if\s+not\s+exists\s+)?[`\"]?(\w+)[`\"]?",
    re.IGNORECASE,
)


class SqlMigrationAdapter:
    name = "sql-migration"
    stacks = ["*"]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        return bool(list(root.rglob("**/db/migration/*.sql")))

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        for sql_path in sorted(root.rglob("**/db/migration/*.sql")):
            service_id = self._service_id(sql_path)
            try:
                content = sql_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            tables = sorted(set(CREATE_TABLE_RE.findall(content)))
            for table in tables:
                items.append(
                    EvidenceItem(
                        type="database_table",
                        source=self.name,
                        subject=f"{service_id}.{table}",
                        attributes={
                            "service": service_id,
                            "table": table,
                            "migration_file": str(sql_path.relative_to(root)),
                        },
                        relations=[EvidenceRelation(relation="belongs_to", target=service_id)],
                        tags=["database", "migration"],
                    )
                )
        return items

    @staticmethod
    def _service_id(sql_path: Path) -> str:
        parts = sql_path.parts
        if "granular-services" in parts:
            idx = parts.index("granular-services")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        for part in reversed(parts):
            if part.endswith("-service"):
                return part
        return sql_path.parents[3].name if len(sql_path.parents) > 3 else "unknown"
