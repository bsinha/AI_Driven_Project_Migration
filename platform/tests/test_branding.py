"""Branding asset tests."""

from __future__ import annotations

from migrate_framework.branding import product_logo_path


def test_product_logo_bundled() -> None:
    path = product_logo_path()
    assert path is not None
    assert path.name == "context-atlas-logo.jpg"
    assert path.stat().st_size > 10_000
