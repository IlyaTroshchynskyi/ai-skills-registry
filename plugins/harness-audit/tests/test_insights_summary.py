from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest

from helpers import SCRIPTS_DIR, load_script

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc).timestamp()


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    return load_script("insights_summary")


def write_session(
    usage: Path,
    sid: str,
    project: str,
    days_ago: float = 1,
    errors: dict[str, int] | None = None,
    friction: dict[str, int] | None = None,
    detail: str = "",
) -> None:
    meta = usage / "session-meta"
    facets = usage / "facets"
    meta.mkdir(parents=True, exist_ok=True)
    facets.mkdir(parents=True, exist_ok=True)
    start = datetime.fromtimestamp(NOW - days_ago * 86400, tz=timezone.utc)
    start_text = start.strftime("%Y-%m-%dT%H:%M:%S.") + f"{start.microsecond // 1000:03d}Z"
    (meta / f"{sid}.json").write_text(
        json.dumps(
            {
                "session_id": sid,
                "project_path": project,
                "start_time": start_text,
                "tool_error_categories": errors or {},
                "bash_would_prompt_count": 1,
                "user_interruptions": 2,
            }
        )
    )
    if friction is not None:
        (facets / f"{sid}.json").write_text(
            json.dumps({"session_id": sid, "friction_counts": friction, "friction_detail": detail})
        )


def test_no_usage_dir_returns_no_data(tmp_path: Path, mod: ModuleType) -> None:
    r = mod.summarize("/x/app", str(tmp_path / "missing"), now=NOW)
    assert r["status"] == "no_data" and r["sessions"] == 0


def test_no_sessions_for_project_returns_no_data(tmp_path: Path, mod: ModuleType) -> None:
    write_session(tmp_path, "s1", "/x/other")
    r = mod.summarize("/x/app", str(tmp_path), now=NOW)
    assert r["status"] == "no_data" and r["sessions"] == 0


def test_prefix_match_counts_worktree_not_sibling(tmp_path: Path, mod: ModuleType) -> None:
    write_session(tmp_path, "s1", "/x/app")
    write_session(tmp_path, "s2", "/x/app/.claude/worktrees/feat")
    write_session(tmp_path, "s3", "/x/app2")
    r = mod.summarize("/x/app", str(tmp_path), now=NOW)
    assert r["sessions"] == 2
    assert "/x/app2" not in r["project_paths"]
    assert r["status"] == "ok"


def test_aggregates_errors_and_friction_by_session_id(tmp_path: Path, mod: ModuleType) -> None:
    write_session(tmp_path, "s1", "/x/app", errors={"Command Failed": 3})
    write_session(
        tmp_path,
        "s2",
        "/x/app",
        errors={"Command Failed": 2, "Other": 1},
        friction={"wrong_approach": 2},
        detail="used npm test instead of make check",
    )
    write_session(tmp_path, "s3", "/x/other", friction={"buggy_code": 5})
    r = mod.summarize("/x/app", str(tmp_path), now=NOW)
    assert r["tool_error_categories"] == {"Command Failed": 5, "Other": 1}
    assert r["friction_counts"] == {"wrong_approach": 2}
    assert r["friction_details"] == ["used npm test instead of make check"]
    assert r["bash_would_prompt_count"] == 2 and r["user_interruptions"] == 4


def test_stale_when_newest_session_older_than_max_age(tmp_path: Path, mod: ModuleType) -> None:
    write_session(tmp_path, "s1", "/x/app", days_ago=40)
    assert mod.summarize("/x/app", str(tmp_path), now=NOW)["status"] == "stale"


def test_unexpected_format_when_no_file_parses(tmp_path: Path, mod: ModuleType) -> None:
    meta = tmp_path / "session-meta"
    meta.mkdir()
    (meta / "a.json").write_text("[1, 2]")
    (meta / "b.json").write_text("not json")
    r = mod.summarize("/x/app", str(tmp_path), now=NOW)
    assert r["status"] == "unexpected_format" and r["skipped_files"] == 2


def test_unexpected_field_types_do_not_crash(tmp_path: Path, mod: ModuleType) -> None:
    meta = tmp_path / "session-meta"
    meta.mkdir()
    (meta / "a.json").write_text(json.dumps({
        "session_id": "a", "project_path": "/x/app", "start_time": "2026-10-16T10:00:00.000Z",
        "tool_error_categories": {"Command Failed": {"nested": 1}}, "bash_would_prompt_count": "x",
        "user_interruptions": None,
    }))
    facets = tmp_path / "facets"
    facets.mkdir()
    (facets / "a.json").write_text(json.dumps({"session_id": "a", "friction_counts": 7}))
    r = mod.summarize("/x/app", str(tmp_path), now=NOW)
    assert r["status"] in ("ok", "unexpected_format")
    assert r["tool_error_categories"] == {} and r["friction_counts"] == {}


def test_relative_repo_path_is_resolved(tmp_path: Path, mod: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "app"
    repo.mkdir()
    write_session(tmp_path / "usage", "s1", str(repo))
    monkeypatch.chdir(repo)
    assert mod.summarize(".", str(tmp_path / "usage"), now=NOW)["sessions"] == 1


def test_cli_prints_json_and_exits_zero(tmp_path: Path) -> None:
    out = subprocess.run(
        [sys.executable, "-I", str(SCRIPTS_DIR / "insights_summary.py"), "/x/app",
         "--usage-dir", str(tmp_path / "missing")],
        capture_output=True, text=True, check=False,
    )
    assert out.returncode == 0
    assert json.loads(out.stdout)["status"] == "no_data"
