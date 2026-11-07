# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A Claude Code plugin marketplace (`troshchynskyi-plugins`, defined in `.claude-plugin/marketplace.json`)
plus `rules/`, rule files that people copy into their own projects' `.claude/rules/`. This repository
does not load `rules/` itself (it has no `.claude/`): they are a deliverable, like the plugins.

There is one plugin, `plugins/harness-audit/`, with one skill, `audit`, run as
`/harness-audit:audit [areas]`. Installing a plugin copies only its folder, so a plugin must be
self-contained, license files included.

## Commands

From `plugins/harness-audit/`:

```bash
python3 -m pytest tests -p no:cacheprovider
python3 -m pytest tests/test_skill_content.py::test_history_module -p no:cacheprovider
claude plugin validate . --strict
claude plugin validate ../.. --strict
```

The last command validates the marketplace at the repository root. Python 3.10+, no dependencies
besides pytest. `-p no:cacheprovider` and `sys.dont_write_bytecode` in `tests/helpers.py` keep caches
out of the skill folder, which ships as is.

Release: bump `version` in `plugins/harness-audit/.claude-plugin/plugin.json`; installed copies update
only when it changes.

## How the audit skill is built

`plugins/harness-audit/skills/audit/` is prompt text the model follows at run time, plus helper
scripts.

- `SKILL.md` is the orchestrator: global rules (read-only, consent, evidence, the "Never recommend"
  list), the script table, the area table and 8 numbered steps. `disable-model-invocation: true`: only
  the user starts it.
- Area files: A–G (`instructions` … `docs`) live in `checklist.md`, with `docs-guide.md` for G; H–K live
  in `modules/` (`skills`, `mechanisms`, `history`, `design-before-code`). Check items have stable IDs
  (`A4`, `G12`, `CTX-C7`, `SK-03`, `HK-07`, `MCP-08`, …) that other files and tests refer to.
- `references/` is shared by all areas: `consent.md` (the single consent message at step 3, command
  timeouts), `subagents.md` (the "Area check" and "Recheck" prompts for steps 4 and 7; subagents do not
  inherit the skill's rules, so whatever they must obey goes into those prompts), `thresholds.md`
  (every numeric threshold, each with a source URL), `applicability.md`, `skill-sources.md`.
- `report-template.md` is the shape of `harness-audit-<YYYY-MM-DD>.md`, the only file the audit writes,
  in the audited repository's root.
- `scripts/*.py` are standalone stdlib-only CLIs, run by the skill as
  `python3 -I ${CLAUDE_SKILL_DIR}/scripts/<name>.py`. `-I` removes the script's directory from
  `sys.path`, so a script cannot import a sibling: keep each one a single file. Tests load them by path
  with `tests/helpers.py:load_script`.

The skill is written in English and tells the model to speak and write the report in the language of
the conversation.

## Tests are a contract on the prose

`tests/test_skill_content.py` asserts that exact phrases appear inside specific sections of the
markdown, found by splitting on headings (`## Rules`, `## Steps`, `### Install`), step markers
(`4. **`) and item markers (`**G5.`). Whitespace is collapsed first, so rewrapping is safe; rewording a
phrase, renaming a heading or renumbering a step is not. Many tests also assert that removed wording
stays gone. When a change is intended, update the assertion in the same change.

Cross-file contracts:

- `MIN_STARS` and `MAX_DAYS_SINCE_PUSH` in `scripts/find_skill_candidates.py` are restated in
  `references/skill-sources.md` and `references/thresholds.md`: change all three together.
- Documentation thresholds are numbers in `references/thresholds.md` only, never in `checklist.md`,
  `docs-guide.md` or the report template.
- Every `modules/…`, `references/…` and `scripts/…` path in backticks in `SKILL.md` must exist.

`tests/test_package.py` guards what gets published:

- No Cyrillic in shipped text (plugin `.md`/`.py`/`.json`, `rules/*.md`, root `README.md`,
  `marketplace.json`). Exceptions: the `WHEN_RE`, `PERSON_RE`, `TOC_RE` regexes in `check_skills.py`,
  which recognise Russian-language skills in audited projects, and fixtures in
  `tests/test_check_skills.py`.
- A `PRIVATE` regex rejects names of the author's private projects, local paths and email in shipped
  files and tests: do not bring examples from other projects into the skill.
- The root and plugin `LICENSE` files are identical; both READMEs keep the install commands; the root
  README lists every file in `rules/`. Tables in `skill-sources.md` are adapted from Apache-2.0
  material, so `THIRD_PARTY_NOTICES.md` and `LICENSES/Apache-2.0.txt` stay.

Markdown prose wraps at 105 columns; tables and frontmatter do not wrap.

## Adding to the registry

- Plugin: `plugins/<name>/` with its own `.claude-plugin/plugin.json` and license files, listed in
  `.claude-plugin/marketplace.json`, with no `marketplace.json` of its own. `test_package.py` expects the
  marketplace to list exactly `harness-audit`, so a second plugin means updating that test.
- Rule: a file in `rules/` plus a row in the root README table. Language rules (`naming-python.md`,
  `naming-js.md`) use `paths:` frontmatter and extend `naming.md`.
