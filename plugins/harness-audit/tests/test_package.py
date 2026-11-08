"""The published repository: manifests, rules, language of the shipped text, nothing private."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = ROOT.parent.parent
REPOSITORY_ADDRESS = "IlyaTroshchynskyi/ai-skills-registry"
RULES = REPOSITORY / "rules"
SKILL_DIR = ROOT / "skills" / "audit"
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
# check_skills.py must recognise Russian-language skills in the projects it audits.
ALLOWED_CYRILLIC = ("WHEN_RE", "PERSON_RE", "TOC_RE")
PRIVATE = re.compile(r"nix-sdlc|harness_development|troshchynskyi|PycharmProjects|IntervAI|crewai-university"
                     r"|docs/superpowers/plans|calibration\.md|gmail\.com"
                     r"|ai_assistant_langchain|langchain-assistant|aiobotocore|table-split|relational-schema"
                     r"|T06\.3|\bM06\b|evals\.md|dynamodb-over", re.IGNORECASE)
SHIPPED_SUFFIXES = {".md", ".py", ".json"}


def shipped_files() -> list[Path]:
    skipped = {"tests", ".git", "__pycache__", ".pytest_cache"}
    plugin = [p for p in ROOT.rglob("*")
              if p.is_file() and p.suffix in SHIPPED_SUFFIXES and not skipped & set(p.relative_to(ROOT).parts)]
    return [*plugin, *RULES.glob("*.md"), REPOSITORY / "README.md", REPOSITORY / ".claude-plugin" / "marketplace.json"]


def manifest(name: str) -> dict:
    return json.loads((ROOT / ".claude-plugin" / name).read_text(encoding="utf-8"))


def marketplace() -> dict:
    return json.loads((REPOSITORY / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))


def test_marketplace_at_the_repository_root_lists_the_plugin_folder() -> None:
    market, plugin = marketplace(), manifest("plugin.json")
    assert market["name"] and market["owner"]["name"]
    assert (plugin["name"], "./plugins/harness-audit") in [(p["name"], p["source"]) for p in market["plugins"]]
    assert re.fullmatch(r"\d+\.\d+\.\d+", plugin["version"])


def test_marketplace_lists_every_plugin_folder() -> None:
    folders = {f"./plugins/{path.name}" for path in (REPOSITORY / "plugins").iterdir()
               if path.is_dir() and not path.name.startswith((".", "__"))}
    assert sorted(entry["source"] for entry in marketplace()["plugins"]) == sorted(folders)


def test_every_listed_plugin_folder_has_a_manifest() -> None:
    for entry in marketplace()["plugins"]:
        assert (REPOSITORY / entry["source"] / ".claude-plugin" / "plugin.json").is_file(), entry["source"]


def test_plugin_folder_has_no_marketplace_of_its_own() -> None:
    assert not (ROOT / ".claude-plugin" / "marketplace.json").exists()


def test_skill_runs_as_harness_audit_colon_audit() -> None:
    assert manifest("plugin.json")["name"] == "harness-audit"
    front = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
    assert re.search(r"^name: audit$", front, re.MULTILINE)
    assert "disable-model-invocation: true" in front


def test_shipped_text_is_in_english() -> None:
    leftovers = [f"{path.relative_to(ROOT)}:{number}"
                 for path in shipped_files()
                 for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                 if CYRILLIC.search(line) and not any(name in line for name in ALLOWED_CYRILLIC)]
    assert not leftovers, leftovers


def test_tests_are_in_english_except_fixtures_of_russian_skills() -> None:
    allowed = {"test_package.py", "test_check_skills.py"}
    leftovers = [f"{path.name}:{number}"
                 for path in sorted((ROOT / "tests").glob("*.py")) if path.name not in allowed
                 for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                 if CYRILLIC.search(line)]
    assert not leftovers, leftovers


def test_nothing_private_is_published() -> None:
    leaks = [f"{path.relative_to(ROOT)}:{number}"
             for path in [*shipped_files(), *(ROOT / "tests").glob("*.py")] if path.name != "test_package.py"
             for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
             if PRIVATE.search(line.replace(REPOSITORY_ADDRESS, ""))
             and "Illia Troshchynskyi" not in line and "troshchynskyi-plugins" not in line]
    assert not leaks, leaks


def test_skill_is_not_tied_to_the_old_name() -> None:
    leftovers = [str(path.relative_to(ROOT)) for path in shipped_files() if "harness-audit-v2" in path.read_text(encoding="utf-8")]
    assert not leftovers, leftovers


def test_person_gets_everything_in_the_language_of_the_conversation() -> None:
    rules = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").split("## Rules")[1].split("## Scripts")[0]
    flat = " ".join(rules.split())
    assert "language of the conversation" in flat and "report" in flat and "consent" in flat


def test_readmes_explain_install_from_this_repository() -> None:
    for readme in (ROOT / "README.md", REPOSITORY / "README.md"):
        text = readme.read_text(encoding="utf-8")
        assert f"claude plugin marketplace add {REPOSITORY_ADDRESS}" in text, readme
        assert "harness-audit@troshchynskyi-plugins" in text and "/harness-audit:audit" in text, readme


def test_reports_stay_out_of_git() -> None:
    for ignore in (ROOT / ".gitignore", REPOSITORY / ".gitignore"):
        text = ignore.read_text(encoding="utf-8")
        assert "__pycache__" in text and "harness-audit-*.md" in text, ignore


def test_registry_keeps_the_naming_rules() -> None:
    assert {path.name for path in RULES.glob("*.md")} >= {"naming.md", "naming-js.md", "naming-python.md"}


def test_language_rules_load_only_for_their_files() -> None:
    assert '- "**/*.py"' in (RULES / "naming-python.md").read_text(encoding="utf-8")
    assert '- "**/*.{js,jsx,ts,tsx}"' in (RULES / "naming-js.md").read_text(encoding="utf-8")


def test_comments_rule_works_outside_the_project_it_came_from() -> None:
    text = (RULES / "comments.md").read_text(encoding="utf-8")
    assert text.startswith("# No comments in code") and "CLAUDE.md" not in text


def test_comments_rule_covers_python_and_javascript() -> None:
    text = (RULES / "comments.md").read_text(encoding="utf-8")
    assert all(marker in text for marker in ("`// ...`", "`# ...`", "JSDoc", "TSDoc", "docstrings"))


def test_comments_rule_keeps_text_that_tools_read() -> None:
    text = (RULES / "comments.md").read_text(encoding="utf-8")
    assert all(marker in text for marker in ("shebang", "`# noqa`", "`# type: ignore`", "`// @ts-expect-error`"))


def test_comments_rule_leaves_out_the_part_about_existing_comments() -> None:
    assert "already in the repository" not in (RULES / "comments.md").read_text(encoding="utf-8")


def test_naming_rule_adds_lookalikes_owner_context_and_pure_answers() -> None:
    text = " ".join((RULES / "naming.md").read_text(encoding="utf-8").split())
    assert "Names do not look alike" in text
    assert "let its owner give the context: `address.state`" in text
    assert "`is_paid` and `check_order_limit` do not write" in text


def test_pure_answer_rule_leaves_get_or_create_valid() -> None:
    text = " ".join((RULES / "naming.md").read_text(encoding="utf-8").split())
    assert "`get_or_create_session`" in text and "If it does both" not in text


def test_readme_lists_every_rule_and_explains_copying() -> None:
    readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
    assert ".claude/rules/" in readme
    assert not [path.name for path in RULES.glob("*.md") if f"`{path.name}`" not in readme]


def test_plugin_is_published_under_mit() -> None:
    assert manifest("plugin.json")["license"] == "MIT"
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License") and "Copyright (c) 2026 Illia Troshchynskyi" in text
    assert "MIT" in (ROOT / "README.md").read_text(encoding="utf-8").split("## License")[1]


def test_repository_root_carries_the_same_license() -> None:
    assert (REPOSITORY / "LICENSE").read_text(encoding="utf-8") == (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT" in (REPOSITORY / "README.md").read_text(encoding="utf-8").split("## License")[1]


def test_adapted_apache_tables_keep_their_license_text() -> None:
    notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "claude-automation-recommender" in notice and "skills/audit/references/skill-sources.md" in notice
    assert "Apache License" in (ROOT / "LICENSES" / "Apache-2.0.txt").read_text(encoding="utf-8")
