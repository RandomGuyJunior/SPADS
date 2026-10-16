#!/usr/bin/env python3
"""Build a Recoil game wrapper from *resolved installed archive names*.

The wrapper inherits BAR through RandomGuy Hosting's dependency. It is a
local test artifact until published as a shared, versioned Rapid game and
selected as the SPADS battle game.
"""
import argparse
from pathlib import Path
import re
import shutil

ARCHIVE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _().+\\-]*$")
def validate(name):
    if not ARCHIVE.fullmatch(name) or len(name) > 200:
        raise ValueError("Expected an installed archive name, not a Rapid tag: " + repr(name))
    return name

def lua_string(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

def generate(foundation, mods):
    foundation = validate(foundation)
    ordered = list(dict.fromkeys(validate(x) for x in mods))
    if foundation in ordered:
        raise ValueError("Hosting foundation cannot also be a custom mod")
    deps = [foundation] + ordered
    lines = [
        "-- Generated from resolved, installed Recoil archive names.",
        "return {",
        '    name = "RandomGuy Modded Battle",',
        '    description = "RandomGuy Hosting with selected mods",',
        '    shortname = "RGMOD",',
        '    mutator = "RandomGuy Mod Stack",',
        '    game = "Beyond All Reason",',
        '    shortGame = "BYAR",',
        '    version = "test",',
        '    modtype = 1,',
        '    depend = {',
        *['        ' + lua_string(dep) + ',' for dep in deps],
        '    },',
        '}',
        '',
    ]
    return "\n".join(lines)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--foundation-archive", required=True,
                   help="Resolved installed name for randomguy-hosting:test")
    p.add_argument("--mod-archive", action="append", default=[],
                   help="Resolved installed mod archive name; repeatable")
    p.add_argument("--modoptions", type=Path, required=True,
                   help="Exported modoptions.lua from RandomGuy Hosting")
    p.add_argument("--output-dir", type=Path, required=True,
                   help="Destination directory ending in .sdd")
    args = p.parse_args()
    if args.output_dir.suffix != ".sdd":
        p.error("--output-dir must end in .sdd")
    if not args.modoptions.is_file():
        p.error("RandomGuy Hosting modoptions.lua export is missing")
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    (output / "modinfo.lua").write_text(
        generate(args.foundation_archive, args.mod_archive), encoding="utf-8")
    shutil.copyfile(args.modoptions, output / "modoptions.lua")
    print("Generated:", output)
    print("This is NOT published or selected as SPADS battle game.")

if __name__ == "__main__":
    main()
