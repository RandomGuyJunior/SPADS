#!/usr/bin/env python3
"""Read-only lookup in RandomGuyJunior/DevelopmentEnvironment's published mod catalogue."""
import argparse
import base64
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CATALOG_URL = "https://api.github.com/repos/RandomGuyJunior/DevelopmentEnvironment/contents/mods.json?ref=main"


def get_mods(url=CATALOG_URL):
    req = Request(url, headers={"User-Agent": "SPADS-mod-catalog-lookup/1.0", "Accept": "application/vnd.github+json", "Cache-Control": "no-cache"})
    with urlopen(req, timeout=12) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
        raise ValueError("Unexpected GitHub Contents API response")
    data = json.loads(base64.b64decode(payload["content"], validate=False))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("mods"), list):
        raise ValueError("Unsupported or malformed mod catalogue")
    return data["mods"]


def lookup(mods, query, include_disabled=False):
    needle = query.strip().casefold()
    if not needle:
        raise ValueError("Mod identifier or name must not be empty")
    results = []
    for mod in mods:
        if not isinstance(mod, dict):
            continue
        if not include_disabled and mod.get("enabled", True) is not True:
            continue
        fields = (mod.get("id"), mod.get("name"), mod.get("rapid_tag"))
        if any(isinstance(field, str) and field.casefold() == needle for field in fields):
            results.append(mod)
    return results


def main():
    parser = argparse.ArgumentParser(description="Look up a mod in the development catalogue, without installing it.")
    parser.add_argument("mod", help="Exact catalogue ID, display name, or Rapid tag")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled catalogue entries")
    parser.add_argument("--catalog-url", default=CATALOG_URL, help="Override source for testing")
    args = parser.parse_args()
    try:
        matches = lookup(get_mods(args.catalog_url), args.mod, args.include_disabled)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Catalogue lookup failed: {exc}", file=sys.stderr)
        return 2
    if not matches:
        print(f"NOT FOUND: {args.mod} (no matching {'entry' if args.include_disabled else 'enabled entry'})")
        return 1
    for mod in matches:
        print(json.dumps({
            key: mod.get(key) for key in
            ("id", "name", "version", "rapid_tag", "rapid_repo", "enabled", "dependencies")
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
