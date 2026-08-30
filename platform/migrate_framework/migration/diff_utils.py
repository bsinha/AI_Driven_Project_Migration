"""Unified diff helpers for assisted task proposals."""

from __future__ import annotations

import difflib


def unified_diff(path: str, before: str | None, after: str, action: str = "create") -> str:
    """Return a unified diff string for review."""
    if action == "create" or before is None:
        before_lines: list[str] = []
    else:
        before_lines = before.splitlines(keepends=True)

    after_lines = after.splitlines(keepends=True)
    label_before = f"a/{path}" if before else "/dev/null"
    label_after = f"b/{path}"
    diff_lines = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=label_before,
        tofile=label_after,
        lineterm="",
    )
    body = "\n".join(diff_lines)
    return body if body else f"(new file {path}, {len(after_lines)} lines)"
