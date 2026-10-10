#!/usr/bin/env python3
"""Deploy reviewed SPADS etc/ configuration without copying repository secrets over live secrets.

Usage: deploy-config.py STAGED_ETC LIVE_ETC
Does not restart SPADS or modify files outside LIVE_ETC (except a pending marker).
"""
import os
import pathlib
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone

if len(sys.argv) != 3:
    sys.exit("Usage: deploy-config.py STAGED_ETC LIVE_ETC")

source = pathlib.Path(sys.argv[1]).resolve()
target = pathlib.Path(sys.argv[2]).resolve()
if not source.is_dir() or not target.is_dir():
    sys.exit("Both staged and live etc directories must exist")

# Explicitly exclude templates and files whose contents are not meant for deployment.
excluded = {"README.MD"}
sensitive = re.compile(r"(password|passwd|secret|token|credential|api.?key|private.?key)", re.I)
assignment = re.compile(r"^(\s*([^\s:#=]+)\s*[:=])(.*?)(\r?\n)?$")
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup = target.parent / ("etc.deploy-backup-" + stamp)
backup.mkdir(mode=0o700)
changed = []

def lines_for(path):
    return path.read_bytes().splitlines(keepends=True)

def setting_map(lines):
    found = {}
    for line in lines:
        decoded = line.decode("utf-8", "replace")
        if decoded.lstrip().startswith("#"):
            continue
        match = assignment.match(decoded)
        if match:
            found[match.group(2).lower()] = match.group(3)
    return found

for staged in sorted(source.iterdir()):
    if not staged.is_file() or staged.is_symlink() or staged.name in excluded:
        continue
    if staged.suffix not in {".conf", ".template"}:
        continue
    live = target / staged.name
    if live.is_symlink():
        sys.exit(f"Refusing symlink target: {live.name}")
    if live.exists() and not live.is_file():
        sys.exit(f"Refusing non-file target: {live.name}")
    staged_lines = lines_for(staged)
    old_lines = lines_for(live) if live.exists() else []
    old_values = setting_map(old_lines)
    result = []
    for line in staged_lines:
        decoded = line.decode("utf-8", "replace")
        match = assignment.match(decoded) if not decoded.lstrip().startswith("#") else None
        if match and sensitive.search(match.group(2)):
            key = match.group(2).lower()
            if key in old_values:
                value = old_values[key]
                line = (match.group(1) + value + (match.group(4) or "")).encode()
            else:
                value = match.group(3).strip()
                if value and not re.fullmatch(r"%[^%]+%|\*+|<[^>]+>", value):
                    sys.exit(f"Refusing to deploy unprotected sensitive field in {staged.name}: {key}")
                # Empty and placeholder values are permitted only when the live file lacks the key.
        result.append(line)
    data = b"".join(result)
    if live.exists() and live.read_bytes() == data:
        continue
    changed.append((live, data))

# Build all backups and candidate files before replacing any live files.
candidates = []
for live, data in changed:
    if live.exists():
        shutil.copy2(live, backup / live.name)
    fd, tmp = tempfile.mkstemp(prefix=".deploy-", dir=target)
    with os.fdopen(fd, "wb") as out:
        out.write(data)
    os.chmod(tmp, (live.stat().st_mode & 0o777) if live.exists() else 0o600)
    candidates.append((pathlib.Path(tmp), live))

for tmp, live in candidates:
    os.replace(tmp, live)

if changed:
    marker = target.parent / ".spads-deployment-pending-restart"
    marker.write_text(stamp + "\n")
print(f"Deployed {len(changed)} configuration files; no SPADS restart performed.")
print(f"Backup directory: {backup}")
