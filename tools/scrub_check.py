#!/usr/bin/env python3
"""Privacy check for klippermaker-publish.

Fails (exit 1) if anything that looks like private data is found.
Run from the repo root:  python3 tools/scrub_check.py

The patterns here are generic on purpose: this file is scanned like every other
file, so it must not contain a real address, hostname or handle itself.
"""
import re
import sys
from pathlib import Path

PATTERNS = {
    "private IP address": r"\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b",
    "absolute home path": r"/home/[A-Za-z0-9._-]+",
    "windows user path": r"(?i)C:\\\\Users\\\\[A-Za-z0-9._-]+",
    "email address": r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b",
    "wifi credential": r"(?i)\b(ssid|psk|wifi[_ ]?password|wpa)\b\s*[:=]\s*\S+",
    "mac address": r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b",
    "hostname or user assignment": r"(?im)^\s*(hostname|user|username|login)\s*[:=]\s*[A-Za-z0-9._-]{3,}",
    "serial number": r"(?i)\bserial[_ ]?(number|no)?\b\s*[:=]\s*[A-Z0-9-]{6,}",
}

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv"}
TEXT_SUFFIXES = {".md", ".py", ".cfg", ".ini", ".json", ".yaml", ".yml", ".txt", ".conf", ""}

# Values that look like private data but are documentation placeholders.
ALLOWED = re.compile(r"<[A-Z_]+>|example\.(com|org)|YOUR_|your-")


def main() -> int:
    root = Path(".")
    findings = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(p in SKIP_DIRS for p in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if ALLOWED.search(line):
                continue
            for label, pattern in PATTERNS.items():
                if re.search(pattern, line):
                    findings.append((str(path), lineno, label, line.strip()[:120]))

    if not findings:
        print("OK - no private data patterns found")
        return 0

    print(f"FAIL - {len(findings)} finding(s):\n")
    for path, lineno, label, line in findings:
        print(f"{path}:{lineno}: [{label}] {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
