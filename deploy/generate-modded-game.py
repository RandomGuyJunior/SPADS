#!/usr/bin/env python3
"""Generate a deterministic Recoil game wrapper for BAR + RandomGuy Hosting + mods.

This writes a modinfo.lua source file. It does NOT publish a Rapid archive or
switch the live SPADS battle: those are separate required activation steps.
"""
import argparse
from pathlib import Path
import re

TAG = re.compile(r"^[A-Za-z0-9_-]+:[A-Za-z0-9_-]+$")

def generate(tags):
    seen = set()
    ordered = []
    for tag in tags:
        if not TAG.fullmatch(tag):
            raise ValueError(f"Invalid Rapid tag: {tag!r}")
        if tag not in seen:
            seen.add(tag)
            ordered.append(tag)
    if any(tag in ("byar:test", "randomguy-hosting:test") for tag in ordered):
        raise ValueError("BAR and RandomGuy Hosting are fixed layers, not custom mods")
    # The hosting game already has rapid://byar:test as its dependency.
    depends = ["rapid://randomguy-hosting:test"] + ["rapid://" + tag for tag in ordered]
    lines = [
        "-- Generated; do not edit by hand.",
        "return {",
        '    name = "RandomGuy Modded Battle",',
        '    description = "RandomGuy Hosting with selected Rapid mods",',
        '    shortname = "RGMOD",',
        '    version = "$VERSION",',
        '    modtype = 1,',
        "    depend = {",
    ]
    lines += ['        "' + dep + '",' for dep in depends]
    lines += ["    },", "}", ""]
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", action="append", default=[], help="Rapid tag, repeatable")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generate(args.mod), encoding="utf-8")

if __name__ == "__main__":
    main()
