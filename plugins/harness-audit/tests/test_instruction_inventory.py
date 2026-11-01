from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from helpers import SCRIPTS_DIR, load_script


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    return load_script("instruction_inventory")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def repo_home(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    home.mkdir()
    return repo, home


def by_path(inv: dict) -> dict[str, dict]:
    return {f["path"]: f for f in inv["files"]}


def test_classifies_files_and_detects_paths_frontmatter(repo_home: tuple[Path, Path], mod: ModuleType) -> None:
    repo, home = repo_home
    write(repo / "CLAUDE.md", "root\n")
    write(repo / ".claude/rules/a.md", '---\npaths: ["src/**"]\n---\nrule a\n')
    write(repo / ".claude/rules/b.md", "rule b\n")
    write(repo / ".claude/skills/s/SKILL.md", "---\nname: s\n---\nbody\n")
    write(repo / ".claude/agents/r.md", "agent\n")
    write(repo / ".claude/settings.json", "{}\n")
    write(repo / ".mcp.json", "{}\n")
    write(repo / "backend/AGENTS.md", "agents\n")
    write(repo / "node_modules/x/CLAUDE.md", "dep\n")
    write(repo / ".claude/worktrees/feat/CLAUDE.md", "copy\n")
    files = by_path(mod.inventory(str(repo), str(home)))
    assert (files[".claude/rules/a.md"]["kind"], files[".claude/rules/a.md"]["has_paths"]) == ("rule", True)
    assert (files[".claude/rules/b.md"]["kind"], files[".claude/rules/b.md"]["has_paths"]) == ("rule", False)
    assert files[".claude/skills/s/SKILL.md"]["kind"] == "skill"
    assert files[".claude/agents/r.md"]["kind"] == "agent"
    assert files[".claude/settings.json"]["kind"] == "settings"
    assert files[".mcp.json"]["kind"] == "mcp"
    assert files["backend/AGENTS.md"]["kind"] == "agents_md"
    assert files["CLAUDE.md"]["has_paths"] is None and files["CLAUDE.md"]["scope"] == "repo"
    assert not any("node_modules" in p or "worktrees" in p for p in files)


def test_startup_chars_include_imports_and_unscoped_rules_only(repo_home: tuple[Path, Path], mod: ModuleType) -> None:
    repo, home = repo_home
    claude_md = "x" * 100 + "\n@docs/a.md\n"
    write(repo / "CLAUDE.md", claude_md)
    write(repo / "docs/a.md", "y" * 36 + "\n@../CLAUDE.md")  # 50 chars, imports back: counted once
    write(repo / ".claude/rules/a.md", '---\npaths: ["src/**"]\n---\n' + "z" * 6)
    write(repo / ".claude/rules/b.md", "w" * 20)
    assert mod.inventory(str(repo), str(home))["startup_chars"] == len(claude_md) + 50 + 20


def test_agents_md_counts_only_without_claude_md(repo_home: tuple[Path, Path], mod: ModuleType) -> None:
    repo, home = repo_home
    write(repo / "AGENTS.md", "a" * 30)
    assert mod.inventory(str(repo), str(home))["startup_chars"] == 30
    write(repo / "CLAUDE.md", "c" * 10)
    assert mod.inventory(str(repo), str(home))["startup_chars"] == 10


def test_personal_files_and_their_imports(repo_home: tuple[Path, Path], mod: ModuleType) -> None:
    repo, home = repo_home
    personal = "p" * 10 + "\n@RTK.md\n"
    write(home / ".claude/CLAUDE.md", personal)
    write(home / ".claude/RTK.md", "r" * 15)
    write(home / ".claude/skills/k/SKILL.md", "skill\n")
    inv = mod.inventory(str(repo), str(home))
    files = by_path(inv)
    assert files["~/.claude/CLAUDE.md"]["scope"] == "personal"
    assert files["~/.claude/CLAUDE.md"]["tracked"] is None
    assert files["~/.claude/skills/k/SKILL.md"]["kind"] == "skill"
    assert inv["startup_chars"] == len(personal) + 15


def test_not_a_git_repo_gives_none_flags(repo_home: tuple[Path, Path], mod: ModuleType) -> None:
    repo, home = repo_home
    write(repo / "CLAUDE.md", "root\n")
    inv = mod.inventory(str(repo), str(home))
    assert inv["git"] is False and all(f["tracked"] is None for f in inv["files"])


def test_gitignored_claude_dir_is_reported(repo_home: tuple[Path, Path], mod: ModuleType) -> None:
    repo, home = repo_home
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    write(repo / ".gitignore", ".claude/\n")
    write(repo / "CLAUDE.md", "root\n")
    write(repo / ".claude/rules/b.md", "rule\n")
    subprocess.run(["git", "-C", str(repo), "add", "CLAUDE.md", ".gitignore"], check=True)
    files = by_path(mod.inventory(str(repo), str(home)))
    assert files[".claude/rules/b.md"]["ignored"] is True and files[".claude/rules/b.md"]["tracked"] is False
    assert files["CLAUDE.md"]["tracked"] is True and files["CLAUDE.md"]["ignored"] is False


def test_worktrees_and_tool_dirs_are_skipped(repo_home: tuple[Path, Path], mod: ModuleType) -> None:
    repo, home = repo_home
    git = ["git", "-C", str(repo)]
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    write(repo / "CLAUDE.md", "root\n")
    subprocess.run([*git, "add", "CLAUDE.md"], check=True)
    subprocess.run([*git, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "init"], check=True)
    subprocess.run([*git, "worktree", "add", "-q", "trees/feat", "-b", "feat"], check=True)
    write(repo / ".worktrees/old/CLAUDE.md", "copy\n")
    write(repo / "venv/lib/CLAUDE.md", "dep\n")
    paths = set(by_path(mod.inventory(str(repo), str(home))))
    assert paths == {"CLAUDE.md"}


def test_cli_prints_json(repo_home: tuple[Path, Path]) -> None:
    repo, home = repo_home
    write(repo / "CLAUDE.md", "root\n")
    out = subprocess.run(
        [sys.executable, "-I", str(SCRIPTS_DIR / "instruction_inventory.py"), str(repo), "--home", str(home)],
        capture_output=True, text=True, check=False,
    )
    assert out.returncode == 0 and json.loads(out.stdout)["startup_chars"] == 5


def test_audit_skill_dirs_are_not_inventoried(repo_home: tuple[Path, Path], mod: ModuleType) -> None:
    repo, home = repo_home
    write(home / ".claude/skills/harness-audit/SKILL.md", "v1\n")
    write(home / ".claude/skills/harness-audit-v2/SKILL.md", "v2\n")
    write(home / ".claude/skills/k/SKILL.md", "skill\n")
    files = by_path(mod.inventory(str(repo), str(home)))
    assert "~/.claude/skills/k/SKILL.md" in files
    assert not any("harness-audit" in p for p in files)
