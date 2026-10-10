#!/usr/bin/env python3
"""Check live Rapid indexes for an exact published package tag (read-only)."""
import argparse
import gzip
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MASTER_URL = "https://randomguyrapid.duckdns.org/repos.gz"
MAX_BYTES = 16 * 1024 * 1024


class LookupError(Exception):
    pass


def fetch_index(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise LookupError("Rapid index URL must use HTTPS")
    request = Request(url, headers={"User-Agent": "SPADS-Rapid-Lookup/1.0", "Cache-Control": "no-cache"})
    with urlopen(request, timeout=12) as response:
        if urlparse(response.geturl()).scheme != "https":
            raise LookupError("Rapid index redirected to non-HTTPS URL")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise LookupError("Rapid index exceeds size limit")
    try:
        decoded = gzip.decompress(raw) if raw.startswith(b"\x1f\x8b") else raw
        if len(decoded) > MAX_BYTES:
            raise LookupError("Decompressed Rapid index exceeds size limit")
        return decoded.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise LookupError("Invalid Rapid index encoding") from exc


def parse_repositories(index):
    repositories = {}
    for line in index.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise LookupError("Malformed repos.gz entry")
        repositories[parts[0]] = parts[1].rstrip("/")
    return repositories


def find_tag(tag, master_url=MASTER_URL, fetch=fetch_index):
    if tag.count(":") != 1 or not all(tag.split(":")) or any(c.isspace() for c in tag):
        raise ValueError("Provide a full Rapid tag such as randomguy-hosting:test")
    repo_name = tag.split(":", 1)[0]
    repos = parse_repositories(fetch(master_url))
    if repo_name not in repos:
        return None
    base_url = repos[repo_name]
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise LookupError("Invalid repository URL in repos.gz")
    versions = fetch(base_url + "/versions.gz")
    for line in versions.splitlines():
        if line.split(",", 1)[0].strip() == tag:
            return line
    return None


def main():
    parser = argparse.ArgumentParser(description="Live, read-only Rapid package existence check")
    parser.add_argument("tag", help="Exact Rapid tag (repo:version)")
    parser.add_argument("--master-url", default=MASTER_URL)
    args = parser.parse_args()
    try:
        result = find_tag(args.tag, args.master_url)
    except (LookupError, ValueError, OSError, TimeoutError) as exc:
        print(f"LOOKUP ERROR: {exc}", file=sys.stderr)
        return 2
    if result is None:
        print(f"NOT PUBLISHED: {args.tag}")
        return 1
    print(f"PUBLISHED: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
