from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest

from helpers import SCRIPTS_DIR, load_script


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    return load_script("run_command")


def test_records_exit_code_and_output_size(tmp_path: Path, mod: ModuleType) -> None:
    r = mod.run("printf 'a\\nb\\n'; exit 3", str(tmp_path), timeout_s=10)
    assert r["exit_code"] == 3 and r["output_lines"] == 2 and r["timed_out"] is False
    assert r["output_bytes"] == 4


def test_stdin_is_closed_so_prompt_does_not_hang(tmp_path: Path, mod: ModuleType) -> None:
    r = mod.run("read x; echo got:$x", str(tmp_path), timeout_s=5)
    assert r["timed_out"] is False and "got:" in r["tail"]


def test_timeout_kills_process_group_including_children(tmp_path: Path, mod: ModuleType) -> None:
    t0 = time.monotonic()
    r = mod.run("sh -c 'sleep 30 & wait'", str(tmp_path), timeout_s=1)
    assert r["timed_out"] is True and r["exit_code"] is None
    assert time.monotonic() - t0 < 3


def test_background_child_does_not_turn_normal_exit_into_timeout(tmp_path: Path, mod: ModuleType) -> None:
    t0 = time.monotonic()
    r = mod.run("sleep 31 & echo main-done; exit 0", str(tmp_path), timeout_s=5)
    assert r["timed_out"] is False and r["exit_code"] == 0 and "main-done" in r["tail"]
    assert time.monotonic() - t0 < 4


def test_child_escaping_group_keeps_partial_output_and_bound(tmp_path: Path, mod: ModuleType) -> None:
    t0 = time.monotonic()
    r = mod.run("echo before; setsid sleep 4", str(tmp_path), timeout_s=1)
    assert r["timed_out"] is True and "before" in r["tail"]
    assert time.monotonic() - t0 < 4


def test_tail_keeps_last_lines(tmp_path: Path, mod: ModuleType) -> None:
    r = mod.run("seq 1 100", str(tmp_path), timeout_s=10, tail_lines=3)
    assert r["tail"].splitlines() == ["98", "99", "100"]


def test_cli_runs_single_shell_string(tmp_path: Path) -> None:
    out = subprocess.run(
        [sys.executable, "-I", str(SCRIPTS_DIR / "run_command.py"), "--cwd", str(tmp_path),
         "--timeout", "10", "--", "printf hi; exit 2"],
        capture_output=True, text=True, check=False,
    )
    assert out.returncode == 0
    result = json.loads(out.stdout)
    assert result["exit_code"] == 2 and result["tail"] == "hi"


def test_cli_keeps_inner_double_dash(tmp_path: Path) -> None:
    out = subprocess.run(
        [sys.executable, "-I", str(SCRIPTS_DIR / "run_command.py"), "--cwd", str(tmp_path),
         "--timeout", "10", "--", "echo", "a", "--", "b"],
        capture_output=True, text=True, check=False,
    )
    assert json.loads(out.stdout)["tail"] == "a -- b"
