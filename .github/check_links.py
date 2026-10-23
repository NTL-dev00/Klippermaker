#!/usr/bin/env python3
"""Fail if any relative markdown link points at a file that does not exist."""
import re
import sys
from pathlib import Path

bad = []
for path in Path(".").rglob("*.md"):
    if any(p in {".git"} for p in path.parts):
        continue
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        target = match.group(1).split("#")[0].strip()
        if not target or "?" in target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if not (path.parent / target).resolve().exists():
            bad.append(f"{path}: {target}")

if bad:
    print("Broken relative links:")
    for item in bad:
        print(" ", item)
    sys.exit(1)

print("All relative links resolve")
