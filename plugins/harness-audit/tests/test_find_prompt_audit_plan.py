from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest

from helpers import SCRIPTS_DIR, load_script

SINCE = 1_800_000_000.0


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    return load_script("find_prompt_audit_plan")


def touch(path: Path, mtime: float) -> None:
    path.write_text("x")
    os.utime(path, (mtime, mtime))


def test_ignores_plans_older_than_since(tmp_path: Path, mod: ModuleType) -> None:
    touch(tmp_path / "prompt-audit-a.md", SINCE - 100)
    touch(tmp_path / "other-plan.md", SINCE + 10)
    assert mod.find_plan(str(tmp_path), SINCE) is None


def test_returns_newest_after_since(tmp_path: Path, mod: ModuleType) -> None:
    touch(tmp_path / "prompt-audit-a.md", SINCE + 5)
    touch(tmp_path / "prompt-audit-b.md", SINCE + 20)
    assert mod.find_plan(str(tmp_path), SINCE).endswith("prompt-audit-b.md")


def test_missing_dir_returns_none(tmp_path: Path, mod: ModuleType) -> None:
    assert mod.find_plan(str(tmp_path / "missing"), SINCE) is None


def test_cli_exit_codes(tmp_path: Path) -> None:
    script = str(SCRIPTS_DIR / "find_prompt_audit_plan.py")
    empty = subprocess.run(
        [sys.executable, "-I", script, "--since", str(SINCE), "--plans-dir", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert empty.returncode == 1 and empty.stdout.strip() == ""
    touch(tmp_path / "prompt-audit-c.md", SINCE + 1)
    found = subprocess.run(
        [sys.executable, "-I", script, "--since", str(SINCE), "--plans-dir", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert found.returncode == 0 and found.stdout.strip().endswith("prompt-audit-c.md")


REPO = "/home/u/Projects/my-sample-app"


def write_report(path: Path, heading: str, mtime: float) -> None:
    path.write_text(f"{heading}\n\n## Context\n", encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_repo_filter_skips_reports_about_other_repos(tmp_path: Path, mod: ModuleType) -> None:
    write_report(tmp_path / "prompt-audit-home-u-projects-cached-nest.md",
                 "# Prompt audit: my-sample-app (2026-10-18)", SINCE + 5)
    write_report(tmp_path / "prompt-audit-home-u-projects-floofy-nautilus.md",
                 "# Prompt audit — other-project (2026-10-17)", SINCE + 20)
    assert mod.find_plan(str(tmp_path), SINCE, REPO).endswith("cached-nest.md")


def test_repo_filter_matches_whole_name_only(tmp_path: Path, mod: ModuleType) -> None:
    write_report(tmp_path / "prompt-audit-home-u-projects-sleepy-quokka.md",
                 "# Prompt audit — my-sample-app-old", SINCE + 5)
    assert mod.find_plan(str(tmp_path), SINCE, REPO) is None


def test_repo_filter_requires_path_prefix_in_file_name(tmp_path: Path, mod: ModuleType) -> None:
    write_report(tmp_path / "prompt-audit-home-other-work-cached-nest.md",
                 "# Prompt audit: my-sample-app", SINCE + 5)
    assert mod.find_plan(str(tmp_path), SINCE, REPO) is None


def test_cli_max_age_days_with_repo(tmp_path: Path) -> None:
    script = str(SCRIPTS_DIR / "find_prompt_audit_plan.py")
    now = time.time()
    old = tmp_path / "prompt-audit-home-u-projects-async-abelson.md"
    write_report(old, "# Prompt audit: my-sample-app", now - 10 * 86400)
    args = [sys.executable, "-I", script, "--max-age-days", "7", "--repo", REPO, "--plans-dir", str(tmp_path)]
    assert subprocess.run(args, capture_output=True, text=True, check=False).returncode == 1
    write_report(tmp_path / "prompt-audit-home-u-projects-cached-nest.md",
                 "# Prompt audit: my-sample-app", now - 2 * 86400)
    found = subprocess.run(args, capture_output=True, text=True, check=False)
    assert found.returncode == 0 and found.stdout.strip().endswith("cached-nest.md")
