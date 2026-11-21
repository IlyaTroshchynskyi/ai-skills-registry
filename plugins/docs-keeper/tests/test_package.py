"""What the plugin publishes: manifests, the skill, the template, language."""
import json
import re
import sys
from pathlib import Path

from helpers import load_script

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = ROOT.parent.parent
REPOSITORY_ADDRESS = "IlyaTroshchynskyi/ai-skills-registry"
SKILL_DIR = ROOT / "skills" / "update"
TEMPLATE = ROOT / "references" / "docs-template.md"
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
# A copy of the regex in plugins/harness-audit/tests/test_package.py: change every copy together.
PRIVATE = re.compile(r"nix-sdlc|harness_development|troshchynskyi|PycharmProjects|IntervAI|crewai-university"
                     r"|docs/superpowers/plans|calibration\.md|gmail\.com"
                     r"|ai_assistant_langchain|langchain-assistant|aiobotocore|table-split|relational-schema"
                     r"|T06\.3|\bM06\b|evals\.md|dynamodb-over", re.IGNORECASE)
SHIPPED_SUFFIXES = {".md", ".py", ".json", ".yaml", ".sh", ".toml"}
DESCRIPTION_LIMIT = 1536
DOCUMENT_KINDS = {"living", "instructions", "generated", "decision", "changelog", "archive"}
DOMAIN_SECTIONS = ["Purpose", "Where it lives", "Contracts", "Flows", "Statuses", "Queue and retries",
                   "External services", "Model calls", "Settings", "Invariants and traps", "Changing it",
                   "Operations"]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def flat(path: Path) -> str:
    return " ".join(read(path).split())


def manifest() -> dict:
    return json.loads(read(ROOT / ".claude-plugin" / "plugin.json"))


def split_frontmatter(path: Path) -> tuple[str, str]:
    _, front, body = read(path).split("---\n", 2)
    return front, body


def shipped_files() -> list[Path]:
    skipped = {"tests", ".git", "__pycache__", ".pytest_cache"}
    return [path for path in ROOT.rglob("*")
            if path.is_file() and path.suffix in SHIPPED_SUFFIXES
            and not skipped & set(path.relative_to(ROOT).parts[:1])]


def layout_rows() -> list[str]:
    layout = read(TEMPLATE).split("## Layout\n")[1].split("\n## ")[0]
    return [line for line in layout.splitlines() if line.startswith("| `") or line.startswith("| nested")]


def test_marketplace_lists_the_plugin_folder() -> None:
    market = json.loads(read(REPOSITORY / ".claude-plugin" / "marketplace.json"))
    plugin = manifest()

    listed = [(entry["name"], entry["source"]) for entry in market["plugins"]]
    entry = next(entry for entry in market["plugins"] if entry["name"] == "docs-keeper")

    assert ("docs-keeper", "./plugins/docs-keeper") in listed
    assert not (ROOT / ".claude-plugin" / "marketplace.json").exists()
    assert entry["description"] == plugin["description"]


def test_manifest_names_the_plugin_and_its_version() -> None:
    plugin = manifest()

    assert plugin["name"] == "docs-keeper"
    assert re.fullmatch(r"\d+\.\d+\.\d+", plugin["version"])


def test_plugin_is_published_under_mit() -> None:
    plugin = manifest()
    license_section = read(ROOT / "README.md").split("## License")[1]

    assert plugin["license"] == "MIT"
    assert read(ROOT / "LICENSE") == read(REPOSITORY / "LICENSE")
    assert "MIT" in license_section


def test_readmes_explain_install_from_this_repository() -> None:
    readmes = {readme: read(readme) for readme in (ROOT / "README.md", REPOSITORY / "README.md")}

    for readme, text in readmes.items():
        assert f"claude plugin marketplace add {REPOSITORY_ADDRESS}" in text, readme
        assert "docs-keeper@troshchynskyi-plugins" in text, readme
        assert "/docs-keeper:update" in text, readme


def test_claude_may_start_the_skill_and_its_description_fits_the_listing() -> None:
    front, _ = split_frontmatter(SKILL_DIR / "SKILL.md")

    description = re.search(r"^description: (.+)$", front, re.MULTILINE).group(1)

    assert re.search(r"^name: update$", front, re.MULTILINE)
    assert "disable-model-invocation" not in front
    assert len(description) <= DESCRIPTION_LIMIT
    assert "Use at the end of every development task that changed code or configuration" in description
    assert "Not for writing documentation from scratch or reorganising it." in description


def test_every_file_the_skill_names_exists() -> None:
    text = read(SKILL_DIR / "SKILL.md")

    skill_paths = set(re.findall(r"\$\{CLAUDE_SKILL_DIR\}/([\w./-]+)", text))
    plugin_paths = set(re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)", text))

    assert skill_paths == {"scripts/scan_docs.py"}
    assert plugin_paths == {"references/docs-template.md"}
    assert all((SKILL_DIR / path).is_file() for path in skill_paths)
    assert all((ROOT / path).is_file() for path in plugin_paths)


def test_skill_runs_its_script_isolated_and_without_a_prompt() -> None:
    front, body = split_frontmatter(SKILL_DIR / "SKILL.md")

    commands = re.findall(r"^python3 .*scan_docs\.py.*$", body, re.MULTILINE)

    assert "allowed-tools: Bash(python3 -I ${CLAUDE_SKILL_DIR}/scripts/scan_docs.py *)" in front
    assert len(commands) == 3
    assert all(command.startswith("python3 -I ${CLAUDE_SKILL_DIR}/") for command in commands)


def test_skill_keeps_its_rules_and_steps() -> None:
    text = read(SKILL_DIR / "SKILL.md")
    skill = flat(SKILL_DIR / "SKILL.md")

    rules = text.split("## Rules\n")[1].split("\n## Steps")[0]
    steps = re.findall(r"^### (\d)\. ", text, re.MULTILINE)
    verify = skill.split("### 7. Verify")[1].split("### 8.")[0]

    for rule in ("**Documents only.**", "**Check against the code as it is now**", "**Smallest true edit.**",
                 "**Only what the code does not show.**", "**An existing page before a new one.**",
                 "**Records are not stale.**", "**Never invent a reason.**", "**Leave git alone.**",
                 "**Language.**"):
        assert rule in rules, rule
    assert "a navigation file such as `mkdocs.yml`" in " ".join(rules.split())
    assert steps == list("12345678")
    assert '"Nothing to update" is a correct result' in skill
    assert "A default that went from 3 to 5 leaves every name in place" in skill
    assert "Never edit by hand." in skill
    assert "only its own status line changes" in skill
    assert "Do not add it unasked." in skill
    assert "If the script answers with `error` instead" in skill
    assert "scan_docs.py impact --base <base_commit from step 1>" in verify


def test_skill_and_script_use_the_same_document_kinds() -> None:
    script_kinds = {kind.value for kind in load_script("scan_docs").DocumentKind}

    skill_kinds = set(re.findall(r"`kind: (\w+)`", read(SKILL_DIR / "SKILL.md")))

    assert script_kinds == DOCUMENT_KINDS
    assert skill_kinds == DOCUMENT_KINDS


def test_script_is_one_file_on_the_standard_library() -> None:
    script = read(SKILL_DIR / "scripts" / "scan_docs.py")

    files = [path.name for path in (SKILL_DIR / "scripts").iterdir() if path.name != "__pycache__"]
    imports = set(re.findall(r"^(?:from|import) ([\w.]+)", script, re.MULTILINE))

    assert files == ["scan_docs.py"]
    assert imports <= {"argparse", "dataclasses", "enum", "fnmatch", "json", "pathlib", "posixpath", "re",
                       "subprocess", "typing", "urllib.parse"}


def test_template_makes_claude_md_the_entry_file() -> None:
    template = read(TEMPLATE)

    prose = re.sub(r"```.*?```", "", template, flags=re.DOTALL)
    headings = re.findall(r"^## (.+)$", prose, re.MULTILINE)

    assert "| `CLAUDE.md` | always |" in template
    assert "| `README.md` | always |" in template
    assert "`CLAUDE.md` then imports it with `@AGENTS.md`" in template
    assert "Never create an empty file" in flat(TEMPLATE)
    assert headings == ["Contents", "Layout", "Parts with a condition", "The agent entry file", "The index",
                        "Document classes", "Writing rules", "Formats", "Quality criteria"]
    assert "There is no total score" in template


def test_template_layout_keeps_docs_in_one_place() -> None:
    rows = layout_rows()

    places = [row.split(" | ")[0] for row in rows]
    claude_row = next(row for row in rows if row.startswith("| `CLAUDE.md`"))
    glossary_row = next(row for row in rows if row.startswith("| `docs/glossary.md`"))

    for place in ["| `docs/<domain>.md`", "| `docs/<area>/`", "| `docs/<task>.md`", "| `README.md` in a code folder",
                  "| `docs/generated/`", "| `docs/runbooks/`", "| nested `CLAUDE.md`"]:
        assert place in places, place
    for gone in ["| `docs/guides/`", "| `docs/archive/`"]:
        assert gone not in places, gone
    assert "`@docs/README.md`" in claude_row
    assert "one for the whole project" in glossary_row
    assert not any(re.search(r"\d", row.replace("NNNN", "")) for row in rows)


def test_template_gives_the_domain_page_fixed_sections_in_order() -> None:
    template = read(TEMPLATE)
    skill = flat(SKILL_DIR / "SKILL.md")

    page = template.split("**Domain page**")[1].split("```markdown\n")[1].split("```")[0]
    rules = flat(TEMPLATE).split("## Writing rules")[1].split("## Formats")[0]

    assert re.findall(r"^## (.+)$", page, re.MULTILINE) == DOMAIN_SECTIONS
    for rule in ("**Fixed section names on a domain page**", "**An invariant names its check**",
                 "**The template applies when a document is touched.**"):
        assert rule in rules, rule
    assert "rename that heading; leave the sections you do not otherwise touch" in skill


def test_template_separates_generated_from_hand_written_reference() -> None:
    template = flat(TEMPLATE)

    generated = template.split("**Generated reference**")[1].split("**Decision**")[0]

    for example in ("`cli.md`", "`config.md`", "`db-schema.md`", "`api.md`", "`metrics.md`", "Do not edit."):
        assert example in generated, example
    assert "Text that an agent or a model wrote is living, not generated" in generated
    assert "there is no archive folder" in template


def test_readme_points_at_the_template_and_cites_its_basis() -> None:
    readme = read(ROOT / "README.md")

    basis = readme.split("## Why it works this way")[1].split("\n## ")[0]

    assert "(references/docs-template.md)" in readme
    assert len(re.findall(r"\]\(https://", basis)) >= 6
    assert "Before you report a task as done, run the `docs-keeper:update` skill." in readme


def test_shipped_text_is_in_english() -> None:
    files = shipped_files()

    leftovers = [f"{path.relative_to(ROOT)}:{number}" for path in files
                 for number, line in enumerate(read(path).splitlines(), 1) if CYRILLIC.search(line)]

    assert not leftovers, leftovers


def test_nothing_private_is_published() -> None:
    files = shipped_files()

    leaks = [f"{path.relative_to(ROOT)}:{number}" for path in files
             for number, line in enumerate(read(path).splitlines(), 1)
             if PRIVATE.search(line.replace(REPOSITORY_ADDRESS, ""))
             and "Illia Troshchynskyi" not in line and "troshchynskyi-plugins" not in line]

    assert not leaks, leaks
