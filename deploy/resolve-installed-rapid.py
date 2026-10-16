#!/usr/bin/env python3
"""Resolve local Rapid tags to verified, installed Recoil archive names.

Reads cached versions.gz indexes and verifies the matching package .sdp
exists under the Spring data directory. No downloads or scans are triggered.
"""
import argparse
import gzip
from pathlib import Path
import re

TAG = re.compile(r"^[A-Za-z0-9_-]+:[A-Za-z0-9_-]+$")
DIGEST = re.compile(r"^[a-fA-F0-9]{32}$")

def resolve(data_dir, tag):
    if not TAG.fullmatch(tag):
        raise ValueError("Invalid Rapid tag")
    data_dir = Path(data_dir).resolve()
    rapid = data_dir / "rapid"
    matches = []
    for index in sorted(rapid.rglob("versions.gz")):
        if not index.is_file():
            continue
        try:
            with gzip.open(index, "rt", encoding="utf-8", errors="replace") as stream:
                for line in stream:
                    parts = line.rstrip("\n\r").split(",", 3)
                    if len(parts) < 4 or parts[0] != tag:
                        continue
                    digest = parts[1].lower()
                    if not DIGEST.fullmatch(digest):
                        raise ValueError("Invalid Rapid package hash for " + tag)
                    package = data_dir / "packages" / (digest + ".sdp")
                    if not package.is_file():
                        raise FileNotFoundError("Rapid archive not installed: " + str(package))
                    archive_name = parts[3].strip()
                    if not archive_name or "\n" in archive_name or "\r" in archive_name:
                        raise ValueError("Missing archive identity for " + tag)
                    matches.append((str(index), digest, archive_name))
        except (OSError, UnicodeError) as error:
            raise RuntimeError("Cannot read Rapid index " + str(index)) from error
    if not matches:
        raise LookupError("Tag not found in cached Rapid indexes: " + tag)
    variants = {(digest, name) for _, digest, name in matches}
    if len(variants) != 1:
        raise ValueError("Ambiguous Rapid tag across indexes: " + tag)
    return matches[0][2], matches[0][1]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", required=True)
    p.add_argument("tags", nargs="+")
    args = p.parse_args()
    for tag in args.tags:
        name, digest = resolve(args.data_dir, tag)
        print(tag + "\t" + digest + "\t" + name)

if __name__ == "__main__":
    main()
