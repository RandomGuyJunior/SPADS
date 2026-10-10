#!/usr/bin/env python3
"""Fail closed on apparent credentials in files shipped to SPADS.

Reports only path, line, and setting name. Never prints values.
"""
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parents[1]
config = root / "etc"
assignment = re.compile(r"^\s*([A-Za-z_][\w.-]*)\s*[:=]\s*(.*?)\s*$")
sensitive = re.compile(r"(?:password|passwd|secret|token|credential|api.?key|private.?key)", re.I)
placeholder = re.compile(r"(?:%[A-Za-z_][\w.-]*%|\$\{[A-Za-z_][\w]*\}|\*{3,}|<[^>]+>)")
problems = []

for path in sorted(config.iterdir()):
    if not path.is_file() or path.is_symlink() or path.suffix not in {".conf", ".template"}:
        continue
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        match = assignment.match(line)
        if not match:
            continue
        key, value = match.groups()
        if not sensitive.search(key):
            continue
        # Shell launcher templates may end with a line-continuation backslash.
        value = value.removesuffix("\\").strip()
        if value and not placeholder.fullmatch(value):
            problems.append((path.relative_to(root), line_number, key))

if problems:
    print("Deployment blocked: possible hardcoded credentials:")
    for path, line, key in problems:
        print(f"  {path}:{line}: {key} (value hidden)")
    sys.exit(1)
print("Credential configuration check passed.")
