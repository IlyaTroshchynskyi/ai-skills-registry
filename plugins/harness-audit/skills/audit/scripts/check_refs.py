"""Broken links and nonexistent commands in instruction files.

Paths come from `backticks` and @import; commands come from `backticks` and code block
lines. Only problems are reported: the path does not exist, the path is tied to someone's
machine, the command is not among package.json scripts, Makefile targets or justfile recipes.

To keep the noise down:
- only tokens with a `/` are checked: a bare file name in instructions is a contextual reference;
- a path counts as existing if, from the root, from the file's directory or as the ending of
  any path in the repository, it points to a file or directory (paths are often written from
  the root of a subproject or module), including without an extension, like TypeScript imports;
- the script does not understand context: a path that the instruction itself calls removed or
  nonexistent is reported too; the model filters those out during the recheck;
- a token without an extension counts as a path only if a directory named after its first
  segment exists somewhere;
- missing paths ignored by git (build output, dependencies) are not reported.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SKIP_DIRS = {".git", "node_modules", "dist", ".venv", "venv", ".worktrees", "worktrees",
             "vendor", "build", "__pycache__"}

PATH_EXTENSIONS = (".md", ".json", ".ts", ".tsx", ".js", ".py", ".yml", ".yaml", ".toml", ".sh")
ABSOLUTE_PREFIXES = ("/home/", "/Users/", "C:\\")
SKIP_MARKERS = ("://", "*", "<", ">", "{", "}")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
IMPORT_RE = re.compile(r"(?<![\w`])@((?:\.{1,2}/|[\w-])[^\s`]*)")
LINE_SUFFIX_RE = re.compile(r":\d+(?::\d+)?$")
COMMAND_RE = re.compile(r"^(npm run|pnpm run|yarn run|pnpm|yarn|make|just)\s+([^\s;&|`]+)")
SEGMENT_SPLIT_RE = re.compile(r"&&|\|\||;|\|")
ENV_PREFIX_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)+")
RUNNER_BUILTINS = {
    "install", "i", "add", "remove", "exec", "dlx", "why", "up", "update",
    "init", "create", "link", "unlink", "run", "dedupe", "outdated", "audit",
    "workspace", "workspaces",
}
DEPENDENCY_FIELDS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
KNOWN_BINARIES = {"typescript": "tsc"}
MAKE_TARGET_RE = re.compile(r"^([A-Za-z0-9_.%/-]+(?:[ \t]+[A-Za-z0-9_.%/-]+)*)[ \t]*:(?![=:])")
JUST_RECIPE_RE = re.compile(r"^@?([A-Za-z0-9_-]+)(?:[ \t]+[^:]*)?:(?!=)")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _package_names(repo: Path) -> tuple[set[str], set[str]]:
    """package.json scripts and package binaries (dependencies and node_modules/.bin)."""
    scripts: set[str] = set()
    binaries: set[str] = set()
    candidates = [repo / "package.json", *repo.glob("*/package.json"), *repo.glob("*/*/package.json")]
    for path in candidates:
        if "node_modules" in path.parts or not path.is_file():
            continue
        bin_dir = path.parent / "node_modules" / ".bin"
        if bin_dir.is_dir():
            binaries.update(p.name for p in bin_dir.iterdir())
        try:
            data = json.loads(_read(path))
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("scripts"), dict):
            scripts.update(data["scripts"])
        for field_name in DEPENDENCY_FIELDS:
            deps = data.get(field_name)
            if isinstance(deps, dict):
                binaries.update(deps)
                binaries.update(KNOWN_BINARIES[d] for d in deps if d in KNOWN_BINARIES)
    return scripts, binaries


def _make_targets(directory: Path) -> set[str]:
    targets: set[str] = set()
    for line in _read(directory / "Makefile").splitlines():
        match = MAKE_TARGET_RE.match(line)
        if match:
            targets.update(match.group(1).split())
    return targets


def _just_recipes(directory: Path) -> set[str]:
    recipes: set[str] = set()
    for name in ("justfile", "Justfile", ".justfile"):
        for line in _read(directory / name).splitlines():
            match = JUST_RECIPE_RE.match(line)
            if match:
                recipes.add(match.group(1))
    return recipes


def _dirs_up_to(repo: Path, start: Path) -> list[Path]:
    """The file's directory and its parents up to and including the repository root."""
    root = repo.resolve()
    current = start.resolve()
    dirs = [current]
    while current != root and root in current.parents:
        current = current.parent
        dirs.append(current)
    if root not in dirs:
        dirs.append(root)
    return dirs


def _commands(span: str) -> list[tuple[str, str]]:
    """Runner commands only at the start of a segment: after `&&`, `;`, `|`, `$ ` or at line start."""
    found: list[tuple[str, str]] = []
    for segment in SEGMENT_SPLIT_RE.split(span):
        segment = segment.strip()
        if segment.startswith("$ "):
            segment = segment[2:].lstrip()
        if not segment or segment.startswith("#"):
            continue
        match = COMMAND_RE.match(ENV_PREFIX_RE.sub("", segment))
        if match:
            found.append((match.group(1), match.group(2)))
    return found


def _clean_ref(token: str) -> str:
    return LINE_SUFFIX_RE.sub("", token.split("#", 1)[0]).rstrip(".,;:)")


@dataclass
class RepoIndex:
    suffixes: set[str] = field(default_factory=set)
    stems: set[str] = field(default_factory=set)
    dir_names: set[str] = field(default_factory=set)


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


def _build_index(repo: Path) -> RepoIndex:
    index = RepoIndex()
    worktrees = _worktree_roots(repo)
    for dirpath, dirnames, filenames in os.walk(repo):
        current = Path(dirpath)
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS
            and not (current.name == ".claude" and d == "worktrees")
            and (current / d).resolve() not in worktrees
        ]
        rel_dir = current.relative_to(repo)
        index.dir_names.update(dirnames)
        for name in [*dirnames, *filenames]:
            parts = (rel_dir / name).parts
            index.suffixes.update("/".join(parts[i:]) for i in range(len(parts)))
        for name in filenames:
            stem_parts = (rel_dir / Path(name).stem).parts
            index.stems.update("/".join(stem_parts[i:]) for i in range(len(stem_parts)))
    return index


def _normalize(ref: str) -> str:
    parts = [p for p in ref.strip("/").split("/") if p not in (".", "..", "")]
    return "/".join(parts)


def _is_gitignored(repo: Path, ref: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "-q", "--", ref],
        capture_output=True, check=False,
    )
    return result.returncode == 0


def _path_problem(repo: Path, file_dir: Path, token: str, index: RepoIndex) -> str | None:
    if any(marker in token for marker in SKIP_MARKERS) or " " in token or token.startswith("~"):
        return None
    if token.startswith(ABSOLUTE_PREFIXES):
        return "absolute_path"
    if token.startswith("/"):
        return None
    ref = _clean_ref(token)
    if "/" not in ref:
        return None
    if (repo / ref).exists() or (file_dir / ref).exists():
        return None
    normalized = _normalize(ref)
    if not normalized or normalized in index.suffixes or normalized in index.stems:
        return None
    first = normalized.split("/", 1)[0]
    if not normalized.endswith(PATH_EXTENSIONS) and first not in index.dir_names:
        return None
    if _is_gitignored(repo, ref):
        return None
    return "missing_path"


def _command_missing(runner: str, name: str, scripts: set[str], binaries: set[str],
                     targets: set[str], recipes: set[str]) -> bool:
    if name.startswith("-"):
        return False
    if runner == "make":
        return name not in targets
    if runner == "just":
        return name not in recipes
    if runner in ("pnpm", "yarn"):
        # `pnpm vitest`, `yarn jest` run a package binary, not only a script
        return name not in RUNNER_BUILTINS and name not in scripts and name not in binaries
    return name not in scripts


def check_refs(repo: str, files: list[str]) -> list[dict[str, Any]]:
    repo_path = Path(repo)
    scripts, binaries = _package_names(repo_path)
    index = _build_index(repo_path)
    targets_cache: dict[Path, set[str]] = {}
    recipes_cache: dict[Path, set[str]] = {}
    problems: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str, str]] = set()

    def report(file_label: str, line_no: int, kind: str, ref: str) -> None:
        key = (file_label, line_no, kind, ref)
        if key not in seen:
            seen.add(key)
            problems.append({"file": file_label, "line": line_no, "kind": kind, "ref": ref})

    for file_name in files:
        path = Path(file_name)
        try:
            file_label = str(path.resolve().relative_to(repo_path.resolve()))
        except ValueError:
            file_label = file_name
        targets: set[str] = set()
        recipes: set[str] = set()
        for directory in _dirs_up_to(repo_path, path.parent):
            targets |= targets_cache.setdefault(directory, _make_targets(directory))
            recipes |= recipes_cache.setdefault(directory, _just_recipes(directory))
        in_fence = False
        for line_no, line in enumerate(_read(path).splitlines(), start=1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            spans = [line] if in_fence else BACKTICK_RE.findall(line)
            for span in spans:
                for runner, name in _commands(span):
                    if _command_missing(runner, name, scripts, binaries, targets, recipes):
                        report(file_label, line_no, "missing_command", f"{runner} {name}")
            if in_fence:
                continue
            # @import is searched only outside `code`: `pnpm add -D @types/node` is not an import
            tokens = [s.strip() for s in spans] + IMPORT_RE.findall(BACKTICK_RE.sub(" ", line))
            for token in tokens:
                kind = _path_problem(repo_path, path.parent, token, index)
                if kind:
                    report(file_label, line_no, kind, token if kind == "absolute_path" else _clean_ref(token))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    print(json.dumps(check_refs(args.repo, args.files), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
