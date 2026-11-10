# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A Claude Code plugin marketplace (`troshchynskyi-plugins`, defined in `.claude-plugin/marketplace.json`)
plus `rules/`, rule files that people copy into their own projects' `.claude/rules/`. This repository
does not load `rules/` itself (it has no `.claude/`): they are a deliverable, like the plugins.

There are two plugins, each with one skill:

- `plugins/harness-audit/`: skill `audit`, run as `/harness-audit:audit [areas]`.
- `plugins/decision-debate/`: skill `decision-debate`, run as `/decision-debate:decision-debate
  <question>`.

Installing a plugin copies only its folder, so a plugin must be self-contained, license files included.

## Commands

From `plugins/harness-audit/`:

```bash
python3 -B -m pytest tests -p no:cacheprovider
python3 -B -m pytest tests/test_skill_content.py::test_history_module -p no:cacheprovider
claude plugin validate . --strict
claude plugin validate ../.. --strict
```

From `plugins/decision-debate/`:

```bash
python3 -B -m pytest tests -p no:cacheprovider
claude plugin validate . --strict
```

`claude plugin validate ../.. --strict` validates the marketplace at the repository root. Python
3.10+, no dependencies besides pytest. `-B` and `-p no:cacheprovider` keep caches out of the plugin
folders, which ship as is.

Release: bump `version` in the plugin's `.claude-plugin/plugin.json`; installed copies update only when
it changes.

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

## How the decision-debate skill is built

`plugins/decision-debate/skills/decision-debate/SKILL.md` is the orchestrator: the main session routes
work between read-only role agents and is the only one that writes files: the report
`docs/solutions/NNNN-<slug>.md` and its working files next to it, in the target project. Any task gets
the full analysis, including one that looks simple. The report is short and at decision level (about
1200 words: the recommendation, 2–3 options, what is easy to miss, how it works); the full design stays
in the final proposal among the working files. Roles, each a subagent in `agents/`: researcher
(one per lens), architect (`SKETCH` and `LEAD` modes: proposal, detail, rebuttal), critic (`REVIEW`,
`LATER-ROUND`, `DEVILS-ADVOCATE`), verifier (one per round, or one per finding in `deep`).

- `--profile lite|standard|deep` sets the cost: researcher budgets, option sketches, rounds, verification
  and the devil's-advocate pass. It does not limit the lenses: the skill chooses them from the task in
  the brief, and the user edits them there. The profile table in `SKILL.md` and the one in `README.md`
  must agree on the agent runs besides researchers: a test compares them.

- `agents/decision-<role>.md` is the only copy of each role prompt: the frontmatter sets the agent's
  tools and model, the body is the role text. The skill sends agents only a Task block.
- `README.md` keeps the sources behind the design ("Why it works this way"). A change that contradicts
  one of them needs a new source there.

## Tests are a contract on the prose

`plugins/harness-audit/tests/test_skill_content.py` asserts that exact phrases appear inside specific
sections of the markdown, found by splitting on headings (`## Rules`, `## Steps`, `### Install`), step
markers (`4. **`) and item markers (`**G5.`). Whitespace is collapsed first, so rewrapping is safe;
rewording a phrase, renaming a heading or renumbering a step is not. Many tests also assert that removed
wording stays gone. When a change is intended, update the assertion in the same change.

Cross-file contracts:

- `MIN_STARS` and `MAX_DAYS_SINCE_PUSH` in `scripts/find_skill_candidates.py` are restated in
  `references/skill-sources.md` and `references/thresholds.md`: change all three together.
- Documentation thresholds are numbers in `references/thresholds.md` only, never in `checklist.md`,
  `docs-guide.md` or the report template.
- Every `modules/…`, `references/…` and `scripts/…` path in backticks in `SKILL.md` must exist.

`plugins/harness-audit/tests/test_package.py` guards what gets published, for that plugin and the
repository root:

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
  `.claude-plugin/marketplace.json` and the root README, with no `marketplace.json` of its own. A test in
  harness-audit fails when a folder in `plugins/` is missing from the marketplace. Give the plugin its
  own `tests/test_package.py` for its manifests, language and privacy, as decision-debate does: the
  `PRIVATE` regex is copied in each, so change all copies together.
- Rule: a file in `rules/` plus a row in the root README table. Language rules (`naming-python.md`,
  `naming-js.md`) use `paths:` frontmatter and extend `naming.md`.
