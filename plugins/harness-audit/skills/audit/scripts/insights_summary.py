"""Summary of /insights data for one repository.

Reads ~/.claude/usage-data/session-meta/*.json and facets/*.json, keeps the sessions
whose project_path is the repository or a path inside it, and sums up tool errors
and friction. The format of these files is undocumented, so the script reports a
status instead of failing on unexpected data.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

MAX_FRICTION_DETAILS = 20


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _belongs_to(project_path: str, repo: str) -> bool:
    root = repo.rstrip("/")
    return project_path == root or project_path.startswith(root + "/")


def _as_int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _int_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {str(k): v for k, v in value.items() if isinstance(v, int) and not isinstance(v, bool)}


def _parse_time(value: str) -> float | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def summarize(repo_path: str, usage_dir: str, now: float, max_age_days: int = 30) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "no_data",
        "sessions": 0,
        "last_session": None,
        "project_paths": [],
        "tool_error_categories": {},
        "friction_counts": {},
        "friction_details": [],
        "bash_would_prompt_count": 0,
        "user_interruptions": 0,
        "skipped_files": 0,
    }
    repo_path = os.path.abspath(repo_path)
    meta_dir = Path(usage_dir) / "session-meta"
    if not meta_dir.is_dir():
        return result

    meta_files = sorted(meta_dir.glob("*.json"))
    sessions: dict[str, dict[str, Any]] = {}
    for path in meta_files:
        data = _load_json(path)
        if not isinstance(data, dict) or not isinstance(data.get("project_path"), str):
            result["skipped_files"] += 1
            continue
        if _belongs_to(data["project_path"], repo_path):
            sessions[str(data.get("session_id", path.stem))] = data

    if meta_files and result["skipped_files"] == len(meta_files):
        result["status"] = "unexpected_format"
        return result
    if not sessions:
        return result

    errors: Counter[str] = Counter()
    friction: Counter[str] = Counter()
    details: list[str] = []
    newest: tuple[float, str] | None = None
    for data in sessions.values():
        errors.update(_int_counts(data.get("tool_error_categories")))
        result["bash_would_prompt_count"] += _as_int(data.get("bash_would_prompt_count"))
        result["user_interruptions"] += _as_int(data.get("user_interruptions"))
        start = data.get("start_time")
        stamp = _parse_time(start) if isinstance(start, str) else None
        if stamp is not None and (newest is None or stamp > newest[0]):
            newest = (stamp, start)

    facets_dir = Path(usage_dir) / "facets"
    for sid in sessions:
        facet = _load_json(facets_dir / f"{sid}.json")
        if not isinstance(facet, dict):
            continue
        friction.update(_int_counts(facet.get("friction_counts")))
        detail = facet.get("friction_detail")
        if isinstance(detail, str) and detail.strip() and len(details) < MAX_FRICTION_DETAILS:
            details.append(detail.strip())

    result.update(
        sessions=len(sessions),
        last_session=newest[1] if newest else None,
        project_paths=sorted({str(d["project_path"]) for d in sessions.values()}),
        tool_error_categories=dict(errors),
        friction_counts=dict(friction),
        friction_details=details,
    )
    stale = newest is None or now - newest[0] > max_age_days * 86400
    result["status"] = "stale" if stale else "ok"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_path")
    parser.add_argument("--usage-dir", default=os.path.expanduser("~/.claude/usage-data"))
    parser.add_argument("--max-age-days", type=int, default=30)
    args = parser.parse_args()
    summary = summarize(args.repo_path, args.usage_dir, now=time.time(), max_age_days=args.max_age_days)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
