#!/usr/bin/env python3
"""Install a published Rapid game package with the headless pr-downloader CLI.

Standalone tool; does not change SPADS game selection or restart any process.
Run as the SPADS service user. Supply --data-dir matching springDataDir.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

LOOKUP = Path(__file__).with_name("mod-catalog-lookup.py")


def validate_tag(tag):
    if not tag or len(tag) > 128 or tag.count(":") != 1:
        raise ValueError("Invalid Rapid tag")
    repo, version = tag.split(":")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_- .")
    if not repo or not version or any(c not in allowed - {" ", "."} for c in repo + version):
        raise ValueError("Invalid Rapid tag")


def load_lookup():
    spec = importlib.util.spec_from_file_location("rapid_lookup", LOOKUP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install(tag, data_dir, downloader="pr-downloader", timeout=1800, dry_run=False):
    validate_tag(tag)
    data = Path(data_dir).expanduser().resolve()
    if not data.is_dir() or not os.access(data, os.W_OK | os.X_OK):
        raise RuntimeError(f"Spring data directory is missing or not writable: {data}")
    tool = shutil.which(downloader)
    if not tool and downloader == "pr-downloader":
        recoil_dir = data.parent / "recoil"
        candidates = sorted(recoil_dir.glob("*/pr-downloader"), reverse=True)
        tool = next((str(p) for p in candidates if p.is_file() and os.access(p, os.X_OK)), None)
    if not tool:
        raise RuntimeError(f"Downloader not found in PATH or Recoil directory: {downloader}")
    lookup = load_lookup()
    published = lookup.find_tag(tag)
    if published is None:
        raise RuntimeError(f"Rapid tag is not published: {tag}")
    # Match the launcher's explicit Rapid repository and disable the streamer.
    rapid_repo = lookup.MASTER_URL
    env = os.environ.copy()
    env["PRD_RAPID_REPO_MASTER"] = rapid_repo
    env["PRD_RAPID_USE_STREAMER"] = "false"

    # Refresh the cached repository index to discover newly published repos.
    from urllib.parse import urlparse
    repo_host = urlparse(rapid_repo).hostname
    cached_index = data / "rapid" / repo_host / "repos.gz"
    if cached_index.is_file():
        cached_index.unlink()

    command = [tool, "--filesystem-writepath", str(data), "--rapid-download", tag]
    print("Published Rapid tag verified:", published.split(",", 1)[0], flush=True)
    print("Downloader:", " ".join(command), flush=True)
    if dry_run:
        return
    result = subprocess.run(command, cwd=data, env=env, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"pr-downloader exited with code {result.returncode}")
    print(f"Download command completed for {tag}. Verify archive resolution before selecting it in SPADS.")


def main():
    parser = argparse.ArgumentParser(description="Install a Rapid mod on the SPADS host")
    parser.add_argument("tag", help="Full published Rapid tag, e.g. randomguy-hosting:test")
    parser.add_argument("--data-dir", required=True, help="SPADS Spring data directory")
    parser.add_argument("--downloader", default="pr-downloader", help="Path/name of headless pr-downloader")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        install(args.tag, args.data_dir, args.downloader, args.timeout, args.dry_run)
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"INSTALL FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
