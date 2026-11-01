"""Inventory of the files that control an agent: in the repository and in personal ~/.claude.

For each file: kind, size, whether git tracks or ignores it, whether a rule has a paths field.
Plus an estimate of how many characters Claude Code loads at session start: root CLAUDE.md
files, personal CLAUDE.md, rules without paths and the targets of their @import.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

SKIP_DIRS = {".git", "node_modules", "dist", ".venv", "venv", ".worktrees", "worktrees",
             "vendor", "build", "__pycache__"}
MAX_IMPORT_DEPTH = 4
AUDIT_SKILL_PREFIX = "harness-audit"  # the audit and its versions are not audited
IMPORT_RE = re.compile(r"(?<![\w`])@((?:~/|\.{1,2}/|[\w-])[^\s`]*)")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _has_paths(text: str) -> bool:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            return False
        if line.startswith("paths:"):
            return True
    return False


def _worktree_roots(repo: Path) -> set[Path]:
    """Roots of linked worktrees inside the repository: they are branch copies, not the project."""
    result = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    main = repo.resolve()
    roots = {Path(line[len("worktree "):]).resolve() for line in result.stdout.splitlines()
             if line.startswith("worktree ")}
    return {root for root in roots if root != main}


def _walk_named(repo: Path, names: set[str]) -> list[Path]:
    found: list[Path] = []
    worktrees = _worktree_roots(repo)
    for dirpath, dirnames, filenames in os.walk(repo):
        current = Path(dirpath)
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS
            and not (current.name == ".claude" and d == "worktrees")
            and (current / d).resolve() not in worktrees
        ]
        found.extend(current / f for f in filenames if f in names)
    return found


def _claude_dir_files(claude_dir: Path) -> list[tuple[Path, str]]:
    patterns = [
        ("rules/**/*.md", "rule"),
        ("skills/*/SKILL.md", "skill"),
        ("agents/*.md", "agent"),
        ("commands/**/*.md", "command"),
    ]
    return [
        (p, kind) for pattern, kind in patterns for p in sorted(claude_dir.glob(pattern))
        if p.is_file() and not (kind == "skill" and p.parent.name.startswith(AUDIT_SKILL_PREFIX))
    ]


def _git_flags(repo: Path, rel_paths: list[str]) -> tuple[bool, set[str], set[str]]:
    probe = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=False,
    )
    if probe.returncode != 0 or Path(probe.stdout.strip()).resolve() != repo.resolve():
        return False, set(), set()
    if not rel_paths:
        return True, set(), set()
    tracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z", "--", *rel_paths],
        capture_output=True, text=True, check=False,
    ).stdout.split("\0")
    ignored = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "-z", "--stdin"],
        input="\0".join(rel_paths), capture_output=True, text=True, check=False,
    ).stdout.split("\0")
    return True, {p for p in tracked if p}, {p for p in ignored if p}


def _imports(path: Path, home: Path) -> list[Path]:
    targets: list[Path] = []
    in_fence = False
    for line in _read(path).splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in IMPORT_RE.finditer(line):
            ref = match.group(1)
            target = home / ref[2:] if ref.startswith("~/") else path.parent / ref
            targets.append(target)
    return targets


def _startup_chars(roots: list[Path], home: Path) -> int:
    seen: set[Path] = set()
    total = 0
    frontier = [(p, 0) for p in roots]
    while frontier:
        path, depth = frontier.pop(0)
        resolved = path.resolve()
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        total += len(_read(resolved))
        if depth < MAX_IMPORT_DEPTH:
            frontier.extend((t, depth + 1) for t in _imports(resolved, home))
    return total


def inventory(repo: str, home: str) -> dict[str, Any]:
    repo_path = Path(repo)
    home_path = Path(home)
    claude_dir = repo_path / ".claude"
    personal_dir = home_path / ".claude"

    repo_entries: list[tuple[Path, str]] = []
    for path in sorted(_walk_named(repo_path, {"CLAUDE.md", "CLAUDE.local.md", "AGENTS.md"})):
        repo_entries.append((path, "agents_md" if path.name == "AGENTS.md" else "claude_md"))
    repo_entries.extend(_claude_dir_files(claude_dir))
    repo_entries.extend((p, "settings") for p in sorted(claude_dir.glob("settings*.json")) if p.is_file())
    if (repo_path / ".mcp.json").is_file():
        repo_entries.append((repo_path / ".mcp.json", "mcp"))

    personal_entries: list[tuple[Path, str]] = []
    if (personal_dir / "CLAUDE.md").is_file():
        personal_entries.append((personal_dir / "CLAUDE.md", "claude_md"))
    personal_entries.extend(_claude_dir_files(personal_dir))

    rel_paths = [str(p.relative_to(repo_path)) for p, _ in repo_entries]
    is_git, tracked, ignored = _git_flags(repo_path, rel_paths)

    files: list[dict[str, Any]] = []
    for (path, kind), rel in zip(repo_entries, rel_paths):
        text = _read(path)
        files.append({
            "path": rel, "scope": "repo", "kind": kind,
            "lines": _count_lines(text), "chars": len(text),
            "tracked": (rel in tracked) if is_git else None,
            "ignored": (rel in ignored) if is_git else None,
            "has_paths": _has_paths(text) if kind == "rule" else None,
        })
    for path, kind in personal_entries:
        text = _read(path)
        files.append({
            "path": "~/" + str(path.relative_to(home_path)), "scope": "personal", "kind": kind,
            "lines": _count_lines(text), "chars": len(text),
            "tracked": None, "ignored": None,
            "has_paths": _has_paths(text) if kind == "rule" else None,
        })

    root_claude = [p for p in (repo_path / "CLAUDE.md", claude_dir / "CLAUDE.md", repo_path / "CLAUDE.local.md") if p.is_file()]
    roots = root_claude or ([repo_path / "AGENTS.md"] if (repo_path / "AGENTS.md").is_file() else [])
    roots += [personal_dir / "CLAUDE.md"]
    roots += [p for p, kind in repo_entries + personal_entries if kind == "rule" and not _has_paths(_read(p))]

    return {"files": files, "startup_chars": _startup_chars(roots, home_path), "git": is_git}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo")
    parser.add_argument("--home", default=os.path.expanduser("~"))
    args = parser.parse_args()
    print(json.dumps(inventory(args.repo, args.home), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
