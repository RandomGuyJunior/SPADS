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
import hashlib
import json
import os
import tempfile
import importlib.util

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
    p.add_argument("--data-dir", type=Path, help="Spring data directory for resolving Rapid tags")
    p.add_argument("--foundation-tag", default="randomguy-hosting:test",
                   help="Hosting Rapid tag (default: randomguy-hosting:test)")
    p.add_argument("--mod", action="append", default=[], help="Custom mod Rapid tag; repeatable")
    p.add_argument("--foundation-archive",
                   help="Explicit resolved archive name (legacy option)")
    p.add_argument("--mod-archive", action="append", default=[],
                   help="Explicit resolved mod archive name (legacy option)")
    p.add_argument("--modoptions", type=Path, required=True,
                   help="Exported modoptions.lua from RandomGuy Hosting")
    p.add_argument("--output-dir", type=Path, required=True,
                   help="Destination directory ending in .sdd")
    args = p.parse_args()
    if args.output_dir.suffix != ".sdd":
        p.error("--output-dir must end in .sdd")
    if not args.modoptions.is_file():
        p.error("RandomGuy Hosting modoptions.lua export is missing")
    foundation = args.foundation_archive
    mod_archives = list(args.mod_archive)
    if args.mod:
        if not args.data_dir:
            p.error("--data-dir is required to resolve Rapid tags")
        resolver_path = Path(__file__).with_name("resolve-installed-rapid.py")
        spec = importlib.util.spec_from_file_location("rapid_archive_resolver", resolver_path)
        resolver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(resolver)
        resolved_foundation, _ = resolver.resolve(args.data_dir, args.foundation_tag)
        if foundation and foundation != resolved_foundation:
            p.error("Foundation archive differs from resolved Rapid tag")
        foundation = resolved_foundation
        for tag in args.mod:
            name, _ = resolver.resolve(args.data_dir, tag)
            mod_archives.append(name)
    if not foundation:
        p.error("Supply --data-dir and --mod or --foundation-archive")
    output = args.output_dir
    manifest = generate(foundation, mod_archives)
    options = args.modoptions.read_bytes()
    fingerprint = hashlib.sha256(manifest.encode("utf-8") + bytes([0]) + options).hexdigest()
    metadata = json.dumps({
        "schema_version": 1,
        "fingerprint": fingerprint,
        "foundation_archive": foundation,
        "mod_archives": list(dict.fromkeys(mod_archives)),
    }, sort_keys=True, indent=2) + chr(10)
    old_info = output / "modinfo.lua"
    old_options = output / "modoptions.lua"
    if (old_info.is_file() and old_options.is_file()
            and old_info.read_text(encoding="utf-8") == manifest
            and old_options.read_bytes() == options):
        print("Unchanged; no archive refresh needed:", output)
        print("Fingerprint:", fingerprint)
        return
    # Stage all content before replacing the wrapper, keeping a usable
    # previous configuration if preparation fails.
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".rgmod-stage-", dir=output.parent) as temp:
        staged = Path(temp)
        (staged / "modinfo.lua").write_text(manifest, encoding="utf-8")
        (staged / "modoptions.lua").write_bytes(options)
        (staged / "rapidmods-state.json").write_text(metadata, encoding="utf-8")
        if output.exists():
            backup = output.with_name(output.name + ".previous")
            if backup.exists():
                shutil.rmtree(backup)
            output.rename(backup)
            try:
                staged.rename(output)
            except BaseException:
                backup.rename(output)
                raise
            shutil.rmtree(backup)
        else:
            staged.rename(output)
    print("Prepared local game wrapper:", output)
    print("Fingerprint:", fingerprint)
    print("Archive refresh required on SPADS before selecting this game.")
    print("Still requires synchronized client wrappers and battle game selection.")

if __name__ == "__main__":
    main()
