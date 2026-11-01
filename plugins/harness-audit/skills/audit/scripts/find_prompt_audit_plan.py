"""Path to the /doctor prompt-audit report for a repository.

prompt-audit writes the full report to ~/.claude/plans/prompt-audit-<path>-<word>-<word>.md, where <path>
is the start of the repository path, and the first line of the report names the repository. The script
takes the newest such file no older than --since (after its own run) or --max-age-days (a ready report).
With --repo, only reports for that repository.
"""

from __future__ import annotations

import argparse
import os
import re
import time
from pathlib import Path


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _first_heading(path: Path) -> str:
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("# "):
                    return line
    except OSError:
        return ""
    return ""


def matches_repo(path: Path, repo: str) -> bool:
    parts = path.stem.removeprefix("prompt-audit-").split("-")
    path_prefix = "-".join(parts[:-2])
    if not path_prefix or not _slug(repo).startswith(path_prefix):
        return False
    name = re.escape(Path(repo).name)
    return re.search(rf"(?<![\w-]){name}(?![\w-])", _first_heading(path), re.IGNORECASE) is not None


def find_plan(plans_dir: str, since: float, repo: str | None = None) -> str | None:
    directory = Path(plans_dir)
    if not directory.is_dir():
        return None
    candidates = [
        (path.stat().st_mtime, path)
        for path in directory.glob("prompt-audit-*.md")
        if path.stat().st_mtime >= since and (repo is None or matches_repo(path, repo))
    ]
    if not candidates:
        return None
    return str(max(candidates)[1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    window = parser.add_mutually_exclusive_group(required=True)
    window.add_argument("--since", type=float)
    window.add_argument("--max-age-days", type=float)
    parser.add_argument("--repo")
    parser.add_argument("--plans-dir", default=os.path.expanduser("~/.claude/plans"))
    args = parser.parse_args()
    since = args.since if args.since is not None else time.time() - args.max_age_days * 86400
    path = find_plan(args.plans_dir, since, os.path.abspath(args.repo) if args.repo else None)
    if path is None:
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
