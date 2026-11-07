# Harness audit checklist: groups A–G

## Contents

- A. Instructions — the base for every stage
- B. Spec to code
- C. Verification — the biggest payoff
- D. Review
- E. Environment and permissions
- F. Hygiene
- G. Documentation

For each item: confirmed, problem or not applicable. Items that do not apply (rule in
`references/applicability.md`) stay out of the report. A problem enters the report only with
evidence: `path:line`, command output or session data.

Every finding has a source (`[own analysis]`, `[prompt-audit]`, `[doctor]`, `[skill-doctor]`,
`[insights]`) and a location: "in repo" (affects the team) or "personal" (only the person's machine).

IDs like `CTX-*`, `CMD-*`, `FB-*` are checks from the research catalogs; numeric thresholds with
sources are in `references/thresholds.md` unless given here.

Scripts (the `scripts/` directory next to `SKILL.md`, run with `python3 -I <path>`):

- `instruction_inventory.py <repo>` — all instruction files of the repository and `~/.claude`: kind,
  size, whether git tracks or ignores them, whether a rule has `paths`; `startup_chars` — how many
  characters load into every session.
- `check_refs.py <repo> <files…>` — broken paths, machine-specific paths, nonexistent
  `npm`/`pnpm`/`yarn`/`make`/`just` commands. The script does not understand context: it also reports
  a path that the instruction itself calls removed or nonexistent ("went away", "none of which
  exist"); read such lines and do not count them as findings.
- `run_command.py --cwd <repo> --timeout <s> -- <command>` — only after consent to run
  (`references/consent.md`): time, exit code, output size, tail.

## A. Instructions — the base for every stage

- **A1. The root file is a short router.** Inside: 1–2 sentences about the project, run and
  verification commands, hard "always / ask / never" rules, links to docs with a "when to read"
  condition. → Move the rest to docs, skills or rules with `paths`.
  - CTX-S1 — length of the root `CLAUDE.md` / `.claude/CLAUDE.md` / `AGENTS.md` (`lines` from the
    inventory), threshold in `references/thresholds.md`.
  - CTX-S2 — total load at startup (`startup_chars`): root, personal `CLAUDE.md`, rules without
    `paths`, `@import` targets. Threshold in `references/thresholds.md`. Measure the sum, not one
    file.
  - CTX-S3 — a file over 4 MiB will not load; only the first 200 lines or 25 KB of `MEMORY.md` are
    read ([Memory](https://code.claude.com/docs/en/memory)).
  - CTX-S4 — if the team also works with Codex: an `AGENTS.md` chain from root to leaf over 32 KiB is
    cut off ([Codex](https://learn.chatgpt.com/docs/agent-configuration/agents-md)).
- **A2. Nested `CLAUDE.md` files are not bloated.** Same threshold as CTX-S1. → Step-by-step
  procedures go to a skill; rules for part of the files go to `.claude/rules` with `paths`; reference
  material goes to `docs/` with a link.
  - CTX-P3 — a procedure in an always-loaded file: a numbered list of ~5 steps or more, or a section
    of ~30 lines or more about one procedure → skill.
  - CTX-P8 — a monorepo (workspaces) with one fat root file and no nested files or scoped rules.
- **A3. Links say when to read.** An agent opens `docs/` on its own only if it recognizes its task in
  the link. → The form "`<file>` — read before `<action>`".
  - CTX-R4 — a file that must always be read is connected in prose ("see AGENTS.md"), not with
    `@import`.
  - Knowledge that must apply in every session belongs in an always-loaded file, not in a skill: a
    skill may not get invoked (SK-20 in `modules/skills.md`).
- **A4. Links are not broken.** Source: `/doctor prompt-audit` if there is consent for it; otherwise
  `check_refs.py` on the repository's instruction files (`scope: repo` in the inventory), which step 2
  runs.
  - CTX-R1 — the path does not exist (`missing_path`).
  - CTX-R5 — a machine-specific path in a committed file (`absolute_path`).
- **A5. Facts are not outdated.** Numbers, versions, lists of files and CI jobs match reality: compare
  with the lockfile and CI config. `prompt-audit` finds wrong versions. → Fix or remove the number
  that will go stale.
- **A6. No contradictions or duplicates** between `CLAUDE.md` files of different levels, rules and
  skills. `prompt-audit` finds contradictions; without consent for it: "not checked". → One place per
  rule.
  - CTX-C11 — wording aimed at old models: caps and pressure, numeric output limits, names of retired
    models. `prompt-audit` finds these; without consent: "not checked".
  - CTX-X2, CTX-X3 — diverged copies and contradictions between tools (`AGENTS.md`, `.cursor/rules`,
    `copilot-instructions.md`).
- **A7. `paths` in rules.** A rule for part of the code without `paths` loads into every session →
  add `paths`. A rule with `paths` whose patterns match no file (`git ls-files`) never loads → fix the
  pattern.
  - CTX-P5 — a rule's frontmatter does not parse (the rule becomes unconditional) or contains foreign
    keys (`globs`, `alwaysApply`, `description`).
  - CTX-P6 — a critical rule ("must", "never") lives only in a nested `CLAUDE.md` or a rule with
    `paths`: after compaction those do not come back until they trigger again. → A line in the root
    file.
- **A8. Project knowledge outside the repository.** Project rules in personal auto memory, in
  `~/.claude/CLAUDE.md` or in files ignored by git (`ignored: true` in the inventory). Colleagues'
  agents do not see them. → Move to a tracked file. Read auto memory only with consent; candidates
  for moving are entries of types `project` and `feedback`.
  - CTX-D2 — significant rules only in Google Docs, Notion, Confluence, Slack.
  - CTX-P7 — personal content in a shared file ("I prefer", "my machine", personal URLs).
- **CTX-X1. `AGENTS.md` is silently ignored.** There is an `AGENTS.md` and a `CLAUDE.md` (or
  `CLAUDE.local.md`) at the same path, and `CLAUDE.md` has no `@AGENTS.md`: Claude Code reads
  `AGENTS.md` only when there is no `CLAUDE.md`. → `CLAUDE.md` with `@AGENTS.md` and a `## Claude Code`
  section; a symlink does not port to Windows.
- **CTX-C7. No verification instructions.** Always-loaded files have no test / typecheck / lint /
  build command. → A line with the verification command and the words "done = this command is green".
- **CTX-C10. Secrets in instruction files.** Tokens, keys, passwords, connection strings with a
  password. Always Critical; do not copy the secret into the report, only `path:line`.
- **CTX-P1. A rule that should be a hook or permission.** "always run", "after every", "before every
  commit", "never edit/commit/push/delete" without a hook, `permissions.deny` or CI step. → A specific
  hook or permission rule (`modules/mechanisms.md`).
- **CTX-P2. A rule duplicates the linter.** Formatting, naming or import-order rules when a linter or
  formatter config exists (`.eslintrc*`, `biome.json`, `ruff.toml`, `.prettierrc`, `.editorconfig`).
  → Remove from the instructions, "What to remove" section.

Outdated documents are checked in G4.

## B. Spec to code

Plans are neither checked nor recommended: not their presence, format or hygiene. Module K
(`modules/design-before-code.md`) checks which tool the person uses to discuss decisions and tasks
with the agent before code. Missing spec files in the repository prove nothing: developers delete
them.

- **B1. The agent knows where the spec is.** The instructions say where specs live (mind `.gitignore`:
  specs may be disposable) and that the agent reads the spec before code. If specs are kept, the place
  is under version control and the path is written in the instructions concretely, not as a wish.
- **B2. Acceptance criteria are verifiable.** There is a requirement that every criterion in a spec
  has a command or test confirming it, and that "done" means "all criteria confirmed". Without this
  the agent decides for itself when it is finished. → A line in the instructions or the spec template:
  "every criterion has a verification command". Do not suggest plan files.
- **B3. A task across several sessions.** Only if there are signs that tasks take longer than one
  session: is there an agreement on a short progress file next to the spec (what is verified, what is
  not, the next step)?
- **B4. The agent sees the tracker task.** An MCP connector or the tracker's CLI is connected and
  mentioned in the instructions, or the team copies acceptance criteria into the spec. → One of the
  two, explicitly. If the project already uses a CLI (`gh`, `glab`), do not recommend an MCP server for
  the same thing (MCP-03).
- **B5. Task boundaries.** The instructions forbid changes outside the task: one task, one branch, no
  drive-by refactoring.

## C. Verification — the biggest payoff

Items that run commands (C8, FB-02, FB-04, CMD-07) run only after consent; without it: "not checked —
no consent". Run every command through `run_command.py` and record the time, exit code and output
size in the report's "Commands run" section.

- **C1. One "verify everything" command.** A script runs format check, lint, typecheck, tests and the
  build, from fast to slow. Without it the agent picks commands itself and skips steps. → Add `check`
  and call it the Definition of Done.
  - CMD-17 — the contract: covers all blocking CI jobs, fail-fast, silent on success; time in
    `references/thresholds.md`.
- **C2. The verifier gives no false green.** No incremental cache producing a false green (for
  example, `tsc -b` without `--force`). If the test runner does not check types, typecheck is part of
  C1.
  - FB-07 — the linter checks only formatting; mass suppressions (`# noqa`, `# type: ignore`,
    `// eslint-disable`, `// @ts-ignore`).
  - FB-08 — types are not strict: no `strict` in `tsconfig.json`, non-strict mypy / pyright.
- **C3. Commands from the instructions exist.** Every command from the instructions is in the scripts,
  and its flags are right. Source: `prompt-audit` or `check_refs.py` (`missing_command`, CTX-R2):
  `npm run`, `pnpm`, `yarn`, `make`, `just`.
- **C4. Write and check commands are not confused.** For example, `format` writes and `format:check`
  checks. The instructions state the difference explicitly.
- **C5. Hooks** — moved to `modules/mechanisms.md`.
- **C6. Hard rules are checked by a machine.** Take the "always / never" rules from the instructions
  and find a lint rule, test, hook or CI step for each. A rule that exists only in text is a candidate.
  Recommend the 1–3 cheapest to automate, with an error message that says how to fix it (ERROR / WHY /
  FIX).
- **C7. End-to-end verification.** Only if the project has a UI or API that can be started. Are there
  e2e or integration tests through the real stack, do they work, do they run in CI, do the instructions
  require them for changes across layers? Broken → recommend 2–3 golden scenarios.
  - E2E-01 — the app does not start headless with one command from a clean worktree.
  - E2E-02 — native `alert(` / `confirm(` dialogs in user flows: an agent working through a browser
    does not see them.
  - E2E-03 — no seed data or test accounts.
- **C8. The baseline is green.** After consent, run the fast parts of C1 through `run_command.py`.
  Record not only the result but also the time, exit code and output size. If a service (a DB) is
  needed: only your own separate container, with separate consent; do not touch the project's
  containers.
- **C9. CI checks the same as the local command.** Extract all `run:` lines from blocking CI jobs and
  match them to task runner commands; a command that lives only in YAML does not exist for the agent
  (FB-01, CI-01). When they diverge, the agent sees green locally and red in CI.
- **CMD-07. Running a single test.** A way to run one file, one test or one package is written down
  and works through the task runner (arguments are passed through). Without it the agent runs the
  whole suite.
- **CMD-08. A fast subset.** `test:changed`, `--onlyChanged`, `nx affected`, `turbo --filter` or
  similar. Matters if a full test run takes longer than ~2 minutes.
- **FB-02. A command does not finish or waits for input.** Expand the wrapper down to the tool and its
  flags: watch mode, confirmations, opening a browser, a pager. After consent, run with a timeout:
  `timed_out: true` or waiting for input is a finding.
- **FB-04. Output does not fit in context.** `output_lines` and `output_bytes` from `run_command.py`
  on success and on failure; thresholds in `references/thresholds.md`. → A quiet mode on success
  (`--silent`, `-q`, an errors-only reporter) or output to a file.
- **FB-11. No written recipe to run and verify.** There is no `.claude/skills/run-*` or
  `.claude/skills/verify/`, although running needs a DB, an env file or a multi-step build. → A recipe
  as a skill (`/run-skill-generator` creates one).

## D. Review

- **D1. The whole team has the review tools.** The commands, skills and agents that review relies on
  live in the repository and are not ignored by git, not only in one developer's `~/.claude`.
- **D2. The reviewer is independent.** Review runs in a fresh context: a subagent that is not a fork,
  or a new session. If the session that wrote the code assembles the report and can discard findings,
  the author has the last word again. → Run review in a new session or a separate subagent.
- **D3. The reviewer gets what it needs:** the diff, the project standards (`CLAUDE.md`, rules) and the
  task spec. A reviewer given only the diff redefines the "spec" on its own.
- **D4. Someone runs the code.** A diff review does not see errors that appear only at runtime. Is the
  output of the C1 command required, and for changes across layers e2e, before or during review?
- **D5. Recurring findings.** Find past review reports (for example `review-*.md` in the root) and
  recent commits with review fixes; the second source is `friction_counts` and
  `tool_error_categories` for this project (`modules/history.md`). Group by type. Turn a type that
  occurs two or more times into a lint rule, test, hook or rule.
- **D6. Review is part of the Definition of Done.** The instructions say when review is mandatory and
  which severity of findings must be fixed before the MR.

## E. Environment and permissions

- **E1. The environment is reproducible.** The runtime version is pinned (`.tool-versions`,
  `mise.toml`, `.nvmrc`, `engines`), the lockfile is in git, services are described in docker-compose
  (ENV-01).
  - ENV-02 — an environment variable is used in code (`process.env.`, `os.environ`, `os.Getenv`) but
    is missing from `.env.example`; a tracked `.env` with a secret is Critical.
- **E2. The project starts without personal cloud access.** If not, the agent cannot run the app to
  verify it. → A local stub; usually a new dependency, "Needs approval".
- **E3. Parallel work.** Only if the person works with parallel sessions or worktrees. Two sessions do
  not break each other's shared test database.
  - ENV-05 — hard-coded ports, `container_name:`, a single dev DB name.
  - ENV-06 — no `.worktreeinclude` when gitignored files are required (`.env`).
- **E4. Permissions** — moved to `modules/mechanisms.md`.
- **E5. `.gitignore`.** Ignores generated reports, `settings.local.json`, the worktree directory
  (`.claude/worktrees/`) and tool working directories (`.superpowers/`), but does not hide the shared
  harness: rules, skills, agents, commands, `settings.json`. Check: `ignored: true` on `scope: repo`
  files in the inventory.

## F. Hygiene

- **F1. Clutter in the root.** Untracked reports and temporary files → delete or add to `.gitignore`.
  The audit's own reports (`harness-audit-*.md`) are not a finding.
- **F2. Excess harness.** The source is usage data, not only "nothing links to it": `/skill-doctor`
  (how many times invoked, cost in context, plugins without use) and unused MCP servers. Every
  component spends context in every session. Recommendations about `~/.claude` are labeled "personal".
  → "What to remove" section.

## G. Documentation

Read `docs-guide.md` before this group: in each recommendation, refer to its rule and explain "why"
using this repository as the example. Diátaxis is our own convention, not confirmed by the research
sources: call it a convention in the report, not a standard. Besides the document type, consider the
loading class: always-loaded (root `CLAUDE.md`), on demand (skills, rules with `paths`, nested files),
reference (`docs/`).

What "I work alone" and a minimal structure cancel and what they do not: `docs-guide.md`,
introduction.

- **G1. The type of each document.** For each `*.md` outside `node_modules` and outside specs: lines,
  level 1–2 headings, Diátaxis type (`docs-guide.md`, section 1). A document with headings of three or
  four types is a candidate for splitting. → What moves where, by section.
- **G2. One fact, one place.** Look for identical sections in the README, `docs/` and `CLAUDE.md`:
  quick start, test commands, project structure, roles, DB schema. Compare the text, not only the
  headings. → Which place stays, where a link replaces it.
  - CTX-C2 — `CLAUDE.md` repeats the README; guideline: more than 40 % overlap.
- **G3. A reference that duplicates the code.** A list of variables when a config schema exists, a DB
  schema when migrations exist, an endpoint list when route schemas exist. → A link to the source or
  generation (`docs-guide.md`, section 3). A procedure only the agent carries out belongs in a skill,
  not in `CLAUDE.md` (CTX-P3).
  - CTX-C3 — a derivable overview in `CLAUDE.md`: a directory tree, dependency lists, per-file
    descriptions. `/doctor` finds it. → "What to remove" section.
- **G4. Outdated documents.** Signs from `docs-guide.md`, section 5: the document itself admits it has
  fallen behind; numbers and versions do not match reality; mentioned paths do not exist. → Fix,
  generate or delete.
  - CTX-F1 — an instruction file unchanged for more than 90 days with more than 100 commits in the
    repository ([unrot](https://github.com/unrot-dev/unrot)).
- **G5. Design docs and specs after implementation.** Do they sit next to current documentation as
  equals? Agents quote outdated entries. Decisions with alternatives recorded in them become ADRs
  during the audit, whether the spec is kept or deleted: the report gives the full text of each
  (`docs-guide.md`, section 4, "Transferring decisions from specs"). The description of working
  behavior goes to a document of the target tree (G10), with a `file:line` link saying where the text
  came from. What happens to the file itself depends on the answer at step 3 (`references/consent.md`)
  "what do you do with specs after implementation":
  - keep or archive → the file goes to `docs/archive/` with a status mark;
  - delete → do not propose `docs/archive/`. If the person is going to delete them ("history", "we
    will delete it later"), that is no reason to skip them but the last chance: they are a source. The
    report gets a table, one row per spec:

    | Spec | ADRs from it (numbers) | Description of working behavior → which document | What to drop |
    | --- | --- | --- | --- |

    Order for each spec: ADRs and the move first, then deletion, in one PR per spec, so the reason is
    never deleted before it is recorded; different specs go in different PRs (`docs-guide.md`,
    section 6).
- **G6. Decisions.** Always checked and always in the report (`docs-guide.md`, section 4): answers
  about readers ("I work alone") or about a minimal structure are no reason to skip G6. The audit
  invents no ADRs: decisions recorded in specs are transferred under G5; for every other decision it
  proposes the practice, and the people who decide write ADRs after the audit. Does the project keep
  ADRs? If not → the folder `docs/decisions/`, the template,
  the line for the root `CLAUDE.md`, what ADRs give this project, and one example ADR on the most
  architecturally significant decision the repository shows (storage, main framework, execution
  model, protocol, an own implementation instead of a ready one), with `file:line` and placeholders
  for what the repository does not say, unless an ADR from G5 already covers it; no such decision →
  the template alone. If it does → no new
  folder: new ADRs go to the project's ADR folder; check the format and the `CLAUDE.md` line. Do not
  propose ADRs for conventions without alternatives.
  - CTX-D3 — an ADR has no status or superseded-by field.
- **G7. Entry points.** A short root README as a map; a README in each top-level code folder; a
  `docs/README.md` table of contents in the form "file — when to read". A table of contents only in
  `CLAUDE.md` is invisible to people.
  - CTX-D1 — a document in `docs/` cannot be reached from the root map in two hops.
- **G8. File names.** The name makes the content and type clear. `notes-2.md`, dates without a topic,
  a generic `misc.md` → rename.
- **G9. Freshness mechanisms.** Docs are updated in the same MR (MR template, a rule in the
  instructions); link checks in CI; section owners. → Propose the lightest option; a new tool is
  "Needs approval". The PR/MR template (`docs-guide.md`, section 7) is G11's recommendation: here
  only note whether it exists; "I work alone" is no reason to drop it.
  - CTX-F3 — no linter for instruction files in CI, pre-commit or a `Stop` hook.
  - CTX-F4 — instruction files only grow: over recent months lines were added but not removed
    (`git log --numstat`).
- **G10. Target structure.** Build the tree according to `docs-guide.md`, section 6: existing content
  with the origin of the text on the right, plus the new documents this audit proposes (ADRs from
  specs, the ADR template and example, the glossary, `docs/README.md`), marked "new"; separately, what
  disappears and why, and the folders for later. Do not propose empty folders.
- **G11. Documentation rules.** Is it written down when, what and where to write (`docs-guide.md`,
  section 7)? Do people (`docs/README.md`, MR template) and the agent see it? The agent's main support
  is a line in the root `CLAUDE.md`: a rule with `paths` on docs triggers only when working with a
  matching file and disappears after compaction. Does git track these files? → A draft section for
  this repository: a "what changed → which document → why" table with real paths only, plus the texts
  for `CLAUDE.md` and the rule. The PR/MR template follows `docs-guide.md`, section 7: with a remote,
  the full text and the line for the root `CLAUDE.md` if there is no template, what to change if there
  is one. This goes into the report even if the rules are complete: "I work alone" is no reason to
  drop the template. It is one recommendation, written here and not under G9.
- **G12. Glossary.** Always, like the ADR practice: if the project has no glossary yet
  (`git ls-files | grep -i glossary`), propose `docs/glossary.md` (`docs-guide.md`, section 2),
  whatever the number of terms. Reader: the agent and a person. Question: "what does X mean in this
  project and what do I call it in new code". Look for:
  - terms used in code, instructions or docs and not explained where they appear: task or module
    codes, internal words for common things ("slot", "golden"), abbreviations;
  - one concept named differently in different places: the naming rule "one word per concept"; the
    entry records the chosen word and the word not to use.

  Sources of terms: enums, table names, codes from the instructions, frequent nouns in `CLAUDE.md` and
  rules. How many entries and how detailed depends on the project's stage and size: an early or small
  project gets the few terms it has now, a large one every term found, grouped by subject area. No
  terms found → the file with the entry format, so terms are added as they appear. → The entries with
  `file:line` and the line for `CLAUDE.md`: "`docs/glossary.md` — read before naming a new domain
  thing". If a glossary exists: check its entries against the format and the terms found.
