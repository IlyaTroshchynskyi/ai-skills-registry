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
    return load_script("check_refs")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    write(root / "docs/a.md", "a\n")
    write(root / "src/a.ts", "x\n")
    write(root / "package.json", json.dumps({"scripts": {"test": "jest", "lint": "eslint ."}}))
    write(root / "backend/package.json", json.dumps({"scripts": {"other-points:try": "tsx x.ts"}}))
    write(root / "Makefile", "VERSION := 1\n.PHONY: lint\nlint:\n\techo ok\n")
    return root


def problems(mod: ModuleType, repo: Path, text: str) -> set[tuple[str, str]]:
    write(repo / "CLAUDE.md", text)
    return {(p["kind"], p["ref"]) for p in mod.check_refs(str(repo), [str(repo / "CLAUDE.md")])}


def test_reports_missing_path_and_command_only(repo: Path, mod: ModuleType) -> None:
    text = "\n".join([
        "`docs/a.md`", "`docs/missing.md`", "see https://x.io/a.md", "`src/**/*.ts`",
        "`<file>.md`", "`~/.claude/x.md`", "`npm run test`", "`npm run nope`",
        "`make lint`", "`/home/u/p/x.md`",
    ])
    assert problems(mod, repo, text) == {
        ("missing_path", "docs/missing.md"),
        ("missing_command", "npm run nope"),
        ("absolute_path", "/home/u/p/x.md"),
    }


def test_import_target_checked(repo: Path, mod: ModuleType) -> None:
    write(repo / "CLAUDE.md", "intro\n@docs/gone.md\n")
    found = mod.check_refs(str(repo), [str(repo / "CLAUDE.md")])
    assert [(p["kind"], p["ref"], p["line"]) for p in found] == [("missing_path", "docs/gone.md", 2)]


def test_non_path_slash_tokens_are_ignored(repo: Path, mod: ModuleType) -> None:
    text = "`application/json` `owner/repo` `feat/xyz` `src/a.ts:42` `and/or`"
    assert problems(mod, repo, text) == set()


def test_bare_names_and_bare_extensions_are_not_checked(repo: Path, mod: ModuleType) -> None:
    write(repo / "backend/src/core/index.ts", "x\n")
    assert problems(mod, repo, "`index.ts` `utils.py` `.ts` `spec.md`") == set()


def test_path_found_as_suffix_anywhere_in_repo(repo: Path, mod: ModuleType) -> None:
    write(repo / "backend/src/modules/audits/service.ts", "x\n")
    write(repo / "backend/app/core/enums.py", "x\n")
    text = "`audits/service.ts` `app/core/enums.py` `audits/gone.ts`"
    assert problems(mod, repo, text) == {("missing_path", "audits/gone.ts")}


def test_module_specifier_without_extension_resolves(repo: Path, mod: ModuleType) -> None:
    write(repo / "frontend/src/api/findings-reports.ts", "x\n")
    assert problems(mod, repo, "`api/findings-reports` `api/gone-reports`") == {
        ("missing_path", "api/gone-reports")
    }


def test_worktree_copy_does_not_mask_broken_reference(repo: Path, mod: ModuleType) -> None:
    write(repo / ".worktrees/feat/docs/old.md", "copy\n")
    write(repo / "venv/lib/docs/older.md", "dep\n")
    assert problems(mod, repo, "`docs/old.md` `docs/older.md`") == {
        ("missing_path", "docs/old.md"), ("missing_path", "docs/older.md")
    }


def test_gitignored_missing_path_is_ignored(repo: Path, mod: ModuleType) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    write(repo / ".gitignore", "node_modules/\n")
    assert problems(mod, repo, "`node_modules/.bin/prettier`") == set()


def test_commands_in_code_fences_workspaces_and_builtins(repo: Path, mod: ModuleType) -> None:
    text = "\n".join([
        "```bash", "make nope", "pnpm install", "npm run other-points:try -w backend -- 1", "```",
        "`make VERSION`", "`yarn lint`",
    ])
    assert problems(mod, repo, text) == {
        ("missing_command", "make nope"),
        ("missing_command", "make VERSION"),
    }


def test_package_binaries_and_workspace_are_not_missing(repo: Path, mod: ModuleType) -> None:
    write(repo / "package.json", json.dumps({
        "scripts": {"test": "jest"},
        "devDependencies": {"vitest": "1", "typescript": "5", "jest": "29", "prisma": "5"},
    }))
    text = "`pnpm vitest run` `pnpm tsc --noEmit` `yarn jest` `pnpm prisma generate` `yarn workspace web build`"
    assert problems(mod, repo, text) == set()


def test_commands_only_at_segment_start(repo: Path, mod: ModuleType) -> None:
    text = "\n".join([
        "```bash", "# just the unit tests", "$ make nope", "make lint && make gone", "CI=1 make lint", "```",
    ])
    got = problems(mod, repo, text)
    assert ("missing_command", "make nope") in got and ("missing_command", "make gone") in got
    assert ("missing_command", "just the") not in got
    assert ("missing_command", "make lint") not in got


def test_nested_makefile_and_just_recipe_with_params(repo: Path, mod: ModuleType) -> None:
    write(repo / "backend/Makefile", "test:\n\tpytest\n")
    write(repo / "justfile", 'test filter="":\n    pytest {{filter}}\n')
    write(repo / "backend/CLAUDE.md", "`make test` `just test`\n")
    found = mod.check_refs(str(repo), [str(repo / "backend/CLAUDE.md")])
    assert found == []


def test_at_sign_inside_code_and_anchors_and_urls(repo: Path, mod: ModuleType) -> None:
    write(repo / "types/x.d.ts", "x\n")
    text = "`pnpm add -D @types/node` `docs/a.md#setup` `https://x.io/docs/a.md` `{var}/x.md` `docs/{name}.md`"
    assert problems(mod, repo, text) == set()


def test_cli_prints_json_list(repo: Path) -> None:
    write(repo / "CLAUDE.md", "`docs/missing.md`\n")
    out = subprocess.run(
        [sys.executable, "-I", str(SCRIPTS_DIR / "check_refs.py"), str(repo), str(repo / "CLAUDE.md")],
        capture_output=True, text=True, check=False,
    )
    assert out.returncode == 0
    assert json.loads(out.stdout) == [
        {"file": "CLAUDE.md", "line": 1, "kind": "missing_path", "ref": "docs/missing.md"}
    ]
