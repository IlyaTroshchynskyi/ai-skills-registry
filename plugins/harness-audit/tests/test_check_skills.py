from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from helpers import SCRIPTS_DIR, load_script

SKILL_DIR = Path(__file__).parent.parent / "skills" / "audit"
GOOD_DESCRIPTION = "Checks DB migrations. Use when creating or checking a migration."


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    return load_script("check_skills")


def make_skill(root: Path, name: str, body: str = "Body.\n", description: str = GOOD_DESCRIPTION,
               extra_fm: str = "", files: dict[str, str] | None = None, dir_name: str | None = None) -> Path:
    skill = root / (dir_name or name)
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n{extra_fm}---\n{body}", encoding="utf-8"
    )
    for rel, text in (files or {}).items():
        (skill / rel).parent.mkdir(parents=True, exist_ok=True)
        (skill / rel).write_text(text, encoding="utf-8")
    return skill


def ids(result: dict) -> set[str]:
    return {i["id"] for i in result["issues"]}


def test_clean_skill_has_no_issues(tmp_path: Path, mod: ModuleType) -> None:
    result = mod.check_skill(str(make_skill(tmp_path, "db-migrations")))
    assert result["issues"] == [] and result["manual"] is False and result["name"] == "db-migrations"


def test_missing_frontmatter_is_sk01(tmp_path: Path, mod: ModuleType) -> None:
    skill = tmp_path / "x"
    skill.mkdir()
    (skill / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")
    assert ids(mod.check_skill(str(skill))) == {"SK-01"}


def test_bad_name_is_sk02(tmp_path: Path, mod: ModuleType) -> None:
    assert "SK-02" in ids(mod.check_skill(str(make_skill(tmp_path, "claude-brief"))))
    assert "SK-02" in ids(mod.check_skill(str(make_skill(tmp_path, "Upper_Case"))))
    assert "SK-02" in ids(mod.check_skill(str(make_skill(tmp_path, "real-name", dir_name="other-dir"))))


def test_description_limits_are_sk03(tmp_path: Path, mod: ModuleType) -> None:
    long_desc = "Use when " + "x" * 1100
    assert "SK-03" in ids(mod.check_skill(str(make_skill(tmp_path, "a", description=long_desc))))
    assert "SK-03" in ids(mod.check_skill(str(make_skill(tmp_path, "b", description="Use when <tag>"))))
    when = "when_to_use: " + "y" * 600 + "\n"
    desc = "Use when " + "z" * 1000
    assert "SK-03" in ids(mod.check_skill(str(make_skill(tmp_path, "c", description=desc, extra_fm=when))))


def test_description_without_when_or_in_first_person_is_sk05(tmp_path: Path, mod: ModuleType) -> None:
    assert "SK-05" in ids(mod.check_skill(str(make_skill(tmp_path, "a", description="DB migrations."))))
    assert "SK-05" in ids(mod.check_skill(str(make_skill(tmp_path, "b", description="I can help when migrations are needed."))))


def test_skills_written_in_russian_are_understood(tmp_path: Path, mod: ModuleType) -> None:
    good = "Проверяет миграции БД. Используй, когда нужна миграция."
    assert "SK-05" not in ids(mod.check_skill(str(make_skill(tmp_path, "a", description=good))))
    assert "SK-05" in ids(mod.check_skill(str(make_skill(tmp_path, "b", description="Миграции БД."))))
    assert "SK-05" in ids(mod.check_skill(str(make_skill(tmp_path, "c", description="Я помогу, когда нужны миграции."))))
    files = {"guide.md": "# Guide\n\n## Содержание\n\n- a\n" + "line\n" * 120}
    assert "SK-12" not in ids(mod.check_skill(str(make_skill(tmp_path, "d", body="`guide.md`\n", files=files))))


def test_manual_skill_is_exempt_from_sk05(tmp_path: Path, mod: ModuleType) -> None:
    result = mod.check_skill(str(make_skill(tmp_path, "a", description="DB migrations.",
                                            extra_fm="disable-model-invocation: true\n")))
    assert result["manual"] is True and "SK-05" not in ids(result)


def test_long_body_is_sk10(tmp_path: Path, mod: ModuleType) -> None:
    assert "SK-10" in ids(mod.check_skill(str(make_skill(tmp_path, "a", body="line\n" * 501))))


def test_reference_structure_is_sk12(tmp_path: Path, mod: ModuleType) -> None:
    body = "See [ref](ref.md) and [no](gone.md). Then `guide.md`.\n"
    files = {
        "ref.md": "mentions deep.md\n",
        "deep.md": "second level\n",
        "orphan.md": "nobody links here\n",
        "guide.md": "## Section\n" + "line\n" * 120,
    }
    issues = [i for i in mod.check_skill(str(make_skill(tmp_path, "a", body=body, files=files)))["issues"]
              if i["id"] == "SK-12"]
    flagged = {i["file"] for i in issues}
    assert flagged == {"SKILL.md", "deep.md", "orphan.md", "guide.md"}
    assert any("gone.md" in i["message"] for i in issues if i["file"] == "SKILL.md")


def test_toc_in_first_lines_satisfies_sk12(tmp_path: Path, mod: ModuleType) -> None:
    files = {"guide.md": "# Guide\n\n## Contents\n\n- a\n" + "line\n" * 120}
    result = mod.check_skill(str(make_skill(tmp_path, "a", body="`guide.md`\n", files=files)))
    assert "SK-12" not in ids(result)


def test_backslash_and_readme_are_sk13(tmp_path: Path, mod: ModuleType) -> None:
    files = {"docs/x.md": "x\n", "README.md": "readme\n"}
    result = mod.check_skill(str(make_skill(tmp_path, "a", body="[x](docs\\x.md) `README.md`\n", files=files)))
    assert "SK-13" in ids(result)


def test_script_without_skill_dir_is_sk15(tmp_path: Path, mod: ModuleType) -> None:
    files = {"scripts/run.py": "print(1)\n"}
    bad = "```bash\npython3 scripts/run.py --x\n```\nScript `scripts/run.py` does it.\n"
    assert "SK-15" in ids(mod.check_skill(str(make_skill(tmp_path, "a", body=bad, files=files))))
    good = "```bash\npython3 ${CLAUDE_SKILL_DIR}/scripts/run.py --x\n```\nScript `scripts/run.py`.\n"
    assert "SK-15" not in ids(mod.check_skill(str(make_skill(tmp_path, "b", body=good, files=files))))


def test_duplicate_descriptions_in_one_root_are_sk07(tmp_path: Path, mod: ModuleType) -> None:
    make_skill(tmp_path, "db-migrations")
    make_skill(tmp_path, "db-migrations-backup", dir_name="db-migrations-backup")
    results = mod.check_skills(str(tmp_path))
    assert len(results) == 2 and all("SK-07" in ids(r) for r in results)


def test_block_scalar_description_is_parsed(tmp_path: Path, mod: ModuleType) -> None:
    skill = tmp_path / "db-migrations"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: db-migrations\ndescription: >-\n  Checks DB migrations.\n  Use when a migration is needed.\n---\nBody.\n",
        encoding="utf-8",
    )
    result = mod.check_skill(str(skill))
    assert result["issues"] == []
    assert result["description_chars"] == len("Checks DB migrations. Use when a migration is needed.")


def test_missing_root_returns_empty_list(tmp_path: Path, mod: ModuleType) -> None:
    assert mod.check_skills(str(tmp_path / "no-skills")) == []


def test_cli_prints_json(tmp_path: Path) -> None:
    make_skill(tmp_path, "db-migrations")
    out = subprocess.run([sys.executable, "-I", str(SCRIPTS_DIR / "check_skills.py"), str(tmp_path)],
                         capture_output=True, text=True, check=False)
    assert out.returncode == 0 and json.loads(out.stdout)[0]["name"] == "db-migrations"


def test_own_skill_has_no_issues(mod: ModuleType) -> None:
    assert mod.check_skill(str(SKILL_DIR))["issues"] == []


def test_audit_skill_dirs_are_skipped_in_root(tmp_path: Path, mod: ModuleType) -> None:
    make_skill(tmp_path, "harness-audit", description="short")
    make_skill(tmp_path, "harness-audit-v2", description="short")
    make_skill(tmp_path, "db-migrations")
    assert [r["name"] for r in mod.check_skills(str(tmp_path))] == ["db-migrations"]
