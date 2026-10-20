"""Optional importer for saved REA web-network-capture Evidence JSON."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import yaml

from migrate_framework.models import EvidenceItem, EvidenceRelation, TechStackProfile


REA_EVIDENCE_ENV = "MATE_REA_EVIDENCE_PATH"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_HTTP_METHOD_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]{1,20}$")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
_OPAQUE_TOKEN_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_-]{24,}$")
_EMAIL_RE = re.compile(r"^[^\s/@]+@[^\s/@]+\.[^\s/@]+$")
_PHONE_RE = re.compile(r"^\+?[0-9(). -]{7,}$")
_MIME_RE = re.compile(
    r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:\s*;\s*charset=[A-Za-z0-9._-]+)?$",
    re.IGNORECASE,
)
_QUERY_VALUE_RE = re.compile(r"([?&][^=&#\s]+)=([^&#\s]*)")
_BEARER_RE = re.compile(r"(?i)\b(bearer|basic)\s+[^\s,;]+")
_URL_USERINFO_RE = re.compile(r"(?i)(https?://)[^/@\s]+:[^/@\s]+@")
_ABSOLUTE_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|/)[^\s,;]+")


class ReaCaptureInputError(ValueError):
    """Raised when a configured REA artifact is malformed or unsupported."""


class ReaCaptureAdapter:
    """Normalize saved REA inspection Evidence into MATE evidence items.

    REA is intentionally not imported or invoked here. Set
    ``MATE_REA_EVIDENCE_PATH`` to a JSON file returned by REA's
    ``inspect-web-network-capture --json`` command to enable this adapter.
    """

    name = "rea_capture"
    stacks = ["*"]

    def can_handle(self, root: Path, profile: TechStackProfile) -> bool:
        return bool(os.environ.get(REA_EVIDENCE_ENV))

    def collect(self, root: Path, profile: TechStackProfile) -> list[EvidenceItem]:
        configured_path = os.environ.get(REA_EVIDENCE_ENV)
        if not configured_path:
            return []
        path = Path(configured_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(
                f"{REA_EVIDENCE_ENV} points to a missing file: {path}"
            )
        try:
            raw_bytes = path.read_bytes()
        except OSError as exc:
            raise ReaCaptureInputError(f"Cannot read REA Evidence file {path}: {exc}") from exc
        if len(raw_bytes) > 32 * 1024 * 1024:
            raise ReaCaptureInputError("REA Evidence JSON exceeds the 32 MiB import limit")
        try:
            payload = json.loads(raw_bytes.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReaCaptureInputError(f"REA Evidence is not valid UTF-8 JSON: {exc}") from exc

        return self.parse(payload, root=root)

    @classmethod
    def parse(cls, payload: Any, *, root: Path) -> list[EvidenceItem]:
        """Parse one portable REA Evidence record (CLI ``--json`` shape)."""
        if not isinstance(payload, dict):
            raise ReaCaptureInputError("REA output must be a JSON Evidence object")
        if payload.get("operation") != "inspect_web_network_capture":
            raise ReaCaptureInputError(
                "Unsupported REA operation; expected inspect_web_network_capture"
            )
        evidence_id = payload.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id or len(evidence_id) > 256:
            raise ReaCaptureInputError("REA Evidence is missing its evidence_id")

        normalized = payload.get("normalized_result")
        if not isinstance(normalized, dict):
            raise ReaCaptureInputError("REA Evidence is missing normalized_result")
        artifact = payload.get("artifact") or normalized.get("artifact")
        if not isinstance(artifact, dict):
            raise ReaCaptureInputError("REA Evidence is missing capture artifact identity")
        artifact_sha = artifact.get("sha256")
        if not isinstance(artifact_sha, str) or not _SHA256_RE.fullmatch(artifact_sha):
            raise ReaCaptureInputError("REA capture artifact must include a SHA-256 digest")
        artifact_sha = artifact_sha.lower()

        records = normalized.get("records")
        if not isinstance(records, list):
            raise ReaCaptureInputError("REA normalized_result.records must be an array")
        if len(records) > 10_000:
            raise ReaCaptureInputError("REA Evidence contains more than 10,000 records")

        manifest = cls._load_service_ports(root)
        records_coverage = normalized.get("coverage")
        limitations = payload.get("limitations", normalized.get("limitations", []))
        if not isinstance(limitations, list):
            limitations = ["REA limitations field was not an array; raw value omitted"]
        safe_limitations = [cls._sanitize_text(str(value))[:500] for value in limitations[:100]]
        safe_limitations.append(
            "Coverage describes records in the supplied capture; it does not establish complete runtime traffic."
        )
        safe_limitations.append(
            "The destination service may be mapped from a landscape port; the caller service is not inferred."
        )
        safe_coverage = cls._coverage_summary(records_coverage)
        parameters = payload.get("parameters")
        parameters = parameters if isinstance(parameters, dict) else {}
        capture_format = parameters.get("format")
        if capture_format != "har":
            raise ReaCaptureInputError(
                "This adapter supports REA HAR inspection Evidence only; parameters.format must be 'har'"
            )
        selected_ordinals = parameters.get("record_ordinals")
        capture_scope = (
            "selected_records"
            if isinstance(selected_ordinals, list)
            else "all_records_in_supplied_capture"
        )

        output: list[EvidenceItem] = []
        seen_ordinals: set[int] = set()
        usable = 0
        excluded = 0
        for record in records:
            if not isinstance(record, dict):
                excluded += 1
                continue
            ordinal = record.get("ordinal")
            if (
                isinstance(ordinal, bool)
                or not isinstance(ordinal, int)
                or ordinal < 0
                or ordinal > 2_147_483_647
            ):
                excluded += 1
                continue
            if ordinal in seen_ordinals:
                raise ReaCaptureInputError(f"Duplicate REA producer record ordinal: {ordinal}")
            seen_ordinals.add(ordinal)

            reported = record.get("reported")
            request = reported.get("request") if isinstance(reported, dict) else None
            if not isinstance(request, dict):
                excluded += 1
                continue
            method = request.get("method")
            url = request.get("url")
            if not isinstance(method, str) or not _HTTP_METHOD_RE.fullmatch(method):
                excluded += 1
                continue
            parsed = cls._safe_url(url)
            if parsed is None:
                excluded += 1
                continue

            method = method.upper()
            host, port, safe_path = parsed
            service_id = manifest.get(port) if port is not None else None
            target = service_id or (f"{host}:{port}" if port is not None else host)
            subject = f"{target}:{method} {safe_path}"
            response = reported.get("response") if isinstance(reported, dict) else None
            response = response if isinstance(response, dict) else {}
            status = response.get("status")
            if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
                status = None
            content = response.get("content")
            mime_type = content.get("mimeType") if isinstance(content, dict) else None
            if not isinstance(mime_type, str) or len(mime_type) > 255 or not _MIME_RE.fullmatch(mime_type):
                mime_type = None
            observed_at = reported.get("startedDateTime") if isinstance(reported, dict) else None
            if not isinstance(observed_at, str) or len(observed_at) > 64:
                observed_at = None
            else:
                try:
                    datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
                except ValueError:
                    observed_at = None

            provider_record_id = str(ordinal)
            stable_id = hashlib.sha256(
                f"{artifact_sha}:{provider_record_id}".encode("utf-8")
            ).hexdigest()[:24]
            rea_provenance = {
                "provider": "REA",
                "operation": "inspect_web_network_capture",
                "provider_evidence_id": evidence_id,
                "provider_record_id": provider_record_id,
                "artifact_sha256": artifact_sha,
                "capture_scope": capture_scope,
                "coverage_status": cls._coverage_status(records_coverage),
                "coverage_meaning": "REA-reported coverage of the supplied capture record set only",
                "limitations": safe_limitations,
                "classification": "observed_request_record",
            }
            attributes: dict[str, Any] = {
                "service": service_id,
                "method": method,
                "path": safe_path,
                "host": host,
                "port": port,
                "response_status": status,
                "mime_type": mime_type,
                "observed_at": observed_at,
                "service_attribution": "landscape_port_match" if service_id else "unmapped",
                "rea": rea_provenance,
            }
            relations = (
                [EvidenceRelation(relation="exposes", target=service_id)]
                if service_id
                else []
            )
            output.append(
                EvidenceItem(
                    id=f"rea-{stable_id}",
                    type="api_endpoint",
                    source=cls.name,
                    subject=subject,
                    confidence=0.9 if service_id else 0.75,
                    attributes=attributes,
                    relations=relations,
                    tags=["api", "observed", "network_capture", "rea"],
                )
            )
            usable += 1

        # Preserve capture identity and coverage even when the capture is empty
        # or every record lacks a usable request line.
        output.insert(
            0,
            EvidenceItem(
                id="rea-" + hashlib.sha256(f"capture:{artifact_sha}".encode()).hexdigest()[:24],
                type="network_capture",
                source=cls.name,
                subject=f"sha256:{artifact_sha}",
                attributes={
                    "provider": "REA",
                    "provider_operation": "inspect_web_network_capture",
                    "provider_evidence_id": evidence_id,
                    "artifact_sha256": artifact_sha,
                    "capture_scope": capture_scope,
                    "coverage_status": cls._coverage_status(records_coverage),
                    "coverage_meaning": "REA-reported coverage of the supplied capture record set only",
                    "record_count_reported": len(records),
                    "record_count_usable": usable,
                    "record_count_excluded": excluded,
                    "provider_coverage": safe_coverage,
                    "limitations": safe_limitations,
                },
                tags=["observed", "network_capture", "rea"],
            ),
        )
        return output

    @staticmethod
    def _coverage_status(coverage: Any) -> str:
        if isinstance(coverage, dict) and coverage.get("status") in {
            "complete",
            "partial",
            "unknown",
            "unsupported",
            "failed",
        }:
            return str(coverage["status"])
        return "unknown"

    @staticmethod
    def _coverage_summary(coverage: Any) -> dict[str, Any] | None:
        if not isinstance(coverage, dict):
            return None
        allowed = {
            "status", "scope", "total_records", "retained_records", "examined_records",
            "excluded_records", "offset", "limit", "next_offset", "exhaustive",
        }
        return {
            key: value
            for key, value in coverage.items()
            if key in allowed
            and isinstance(value, (str, int, float, bool, type(None)))
            and (not isinstance(value, str) or len(value) <= 200)
            and (not isinstance(value, int) or isinstance(value, bool) or abs(value) <= 2**53)
            and (not isinstance(value, float) or math.isfinite(value))
        }

    @staticmethod
    def _sanitize_text(value: str) -> str:
        value = _BEARER_RE.sub(r"\1 [redacted]", value)
        value = _URL_USERINFO_RE.sub(r"\1[redacted]@", value)
        value = _QUERY_VALUE_RE.sub(r"\1=[redacted]", value)
        return _ABSOLUTE_PATH_RE.sub("[path redacted]", value)

    @staticmethod
    def _safe_url(value: Any) -> tuple[str, int | None, str] | None:
        if not isinstance(value, str) or len(value) > 16_384:
            return None
        try:
            parts = urlsplit(value)
            if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
                return None
            host = parts.hostname.lower()
            if len(host) > 255:
                return None
            port = parts.port if parts.port is not None else (443 if parts.scheme.lower() == "https" else 80)
        except ValueError:
            return None
        path = parts.path or "/"
        safe_segments = []
        for segment in path.split("/"):
            decoded = unquote(segment)
            if (
                decoded.isdigit()
                or _UUID_RE.fullmatch(decoded)
                or _OPAQUE_TOKEN_RE.fullmatch(decoded)
                or _EMAIL_RE.fullmatch(decoded)
                or _PHONE_RE.fullmatch(decoded)
            ):
                safe_segments.append("{redacted}")
            else:
                safe_segments.append(segment[:256])
        return host, port, "/".join(safe_segments)[:2048]

    @staticmethod
    def _load_service_ports(root: Path) -> dict[int, str]:
        candidates = [root / "landscape-manifest.yaml", root / "landscape-manifest.yml"]
        if not any(path.is_file() for path in candidates):
            candidates.extend([root / "sample-bank" / "landscape-manifest.yaml", root / "sample-bank" / "landscape-manifest.yml"])
        for path in candidates:
            if not path.is_file():
                continue
            try:
                doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue
            result: dict[int, str] = {}
            for service in doc.get("services") or []:
                if not isinstance(service, dict):
                    continue
                port = service.get("port")
                service_id = service.get("id")
                if isinstance(port, int) and not isinstance(port, bool) and isinstance(service_id, str):
                    result[port] = service_id
            return result
        return {}
