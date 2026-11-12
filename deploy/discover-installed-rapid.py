#!/usr/bin/env python3
"""List installed optional Rapid mods from cached indexes and .sdp manifests.

Read-only: a tag is reported only when its indexed package manifest exists.
No remote requests or downloads are performed.
"""
import argparse
import gzip
from pathlib import Path
import re
import sys

TAG = re.compile(r"^dev-mods:[A-Za-z0-9_-]+$")
HASH = re.compile(r"^[0-9a-fA-F]{32}$")


def discover(data_dir):
    data = Path(data_dir).resolve()
    rapid = data / "rapid"
    packages = data / "packages"
    installed = set()
    if not rapid.is_dir() or not packages.is_dir():
        return installed
    for index in sorted(rapid.rglob("versions.gz")):
        try:
            with gzip.open(index, "rt", encoding="utf-8") as source:
                for line in source:
                    fields = line.rstrip("\r\n").split(",", 3)
                    if len(fields) != 4:
                        continue
                    tag, digest = fields[:2]
                    if TAG.fullmatch(tag) and HASH.fullmatch(digest):
                        if (packages / (digest.lower() + ".sdp")).is_file():
                            installed.add(tag)
        except (OSError, UnicodeError) as exc:
            raise RuntimeError(f"Cannot read Rapid index {index}: {exc}") from exc
    return installed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    args = parser.parse_args()
    try:
        for tag in sorted(discover(args.data_dir)):
            print(tag)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
