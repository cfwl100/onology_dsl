#!/usr/bin/env python3
"""Repo-level static check for Python file header regressions.

Checks all ``*.py`` files to ensure:
1) File is UTF-8 decodable.
2) File does not start with a backslash character (the regression we fixed).
"""

from __future__ import annotations

from pathlib import Path
import sys


EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "venv"}


def iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    errors: list[str] = []

    for path in sorted(iter_py_files(root)):
        data = path.read_bytes()

        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"[encoding] {path}: not UTF-8 decodable ({exc})")
            continue

        if data.startswith(b"\\"):
            errors.append(f"[header] {path}: first character is a backslash")

    if errors:
        print("Python header check failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Python header check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
