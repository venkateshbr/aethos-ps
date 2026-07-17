#!/usr/bin/env python3
"""Generate docker-compose.hostinger.registry.yml from docker-compose.hostinger.yml.

The registry compose is identical to the base Hostinger compose but with every
`build:` block removed, so a Hostinger Docker Manager CLONE deploy PULLS the
prebuilt public GHCR images instead of building on the VPS. Keep it committed and
in sync — the deploy workflow regenerates it and fails if it drifted.

Usage: python scripts/deploy/gen-registry-compose.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docker-compose.hostinger.yml"
OUT = ROOT / "docker-compose.hostinger.registry.yml"

HEADER = (
    "# GENERATED companion to docker-compose.hostinger.yml — REGISTRY/PULL ONLY.\n"
    "# Identical to docker-compose.hostinger.yml but with every `build:` block\n"
    "# removed, so the Hostinger Docker Manager PULLS the prebuilt public GHCR\n"
    "# images (ghcr.io/venkateshbr/aethos-ps-*:$AETHOS_IMAGE_TAG) instead of\n"
    "# building on the VPS. The clone still supplies the .env for interpolation.\n"
    "# Regenerate with: python scripts/deploy/gen-registry-compose.py\n"
    "# See docs/infra/HOSTINGER_DEPLOYMENT.md.\n"
)


def strip_build_blocks(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    skip_indent: int | None = None
    i = 0
    while i < len(lines):
        ln = lines[i]
        stripped = ln.strip()
        indent = len(ln) - len(ln.lstrip())
        if skip_indent is not None:
            if stripped == "" or indent > skip_indent:
                i += 1
                continue
            skip_indent = None
        if re.match(r"^\s*build:\s*$", ln):
            skip_indent = indent
            i += 1
            continue
        out.append(ln)
        i += 1
    return "\n".join(out)


def main() -> None:
    body = strip_build_blocks(SRC.read_text())
    OUT.write_text(HEADER + body)
    leaked = [
        ln
        for ln in body.split("\n")
        if not ln.lstrip().startswith("#") and re.match(r"^\s*build:\s*$", ln)
    ]
    assert not leaked, "build: block leaked into registry compose"
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
