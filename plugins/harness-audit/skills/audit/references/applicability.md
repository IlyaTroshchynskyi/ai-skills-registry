# Applicability of checks

The main protection against irrelevant content in the report. Checks that do not apply do not run and
stay out of the findings and "Checked and fine" sections. An area that does not apply at all gets one
line "not applicable: why" in the "Summary" table.

## Project profile (step 1)

Collect before the checks. Ask at step 6 about whatever the repository and the person's setup do not
reveal.

| Field | From where |
| --- | --- |
| Stack and languages | Manifests, file extensions |
| Type | Web app with UI, API service, library, CLI, infrastructure, monorepo (workspaces) |
| Size | Number of code files, number of packages |
| CI provider | `.github/workflows/`, `.gitlab-ci.yml` and the like |
| Team process | Instructions, CONTRIBUTING, MR/PR templates, `git log` |
| Design-before-code tool | Module K (`modules/design-before-code.md`) |
| Parallel work | `.claude/worktrees/`, `git worktree list`, several worktree `project_path` values in the history |
| Session history | Whether it exists (`modules/history.md`, "Is there history") |

## Agent practices are always checked

A missing practice is a gap to recommend closing, not "not applicable":

- designing decisions and tasks with the agent before code (module K);
- review (group D);
- instructions (A), verification commands and tests (C);
- environment (E), permissions and secrets, hooks (module I);
- skills (module H);
- hygiene (F), documentation (G).

The practice is identified by the person's tools (plugins, skills, agents, invocations in the history),
not by artifacts in the repository. Missing spec files prove nothing: developers delete them.

## Conditional checks

Run only when the condition holds:

| Check | Condition |
| --- | --- |
| C7, E2E-01…03 — end-to-end verification, e2e | The project has a UI or API that can be started |
| E3, ENV-05, ENV-06 — parallel work, worktrees | The person works with parallel sessions or worktrees |
| `SP-*` — Superpowers prerequisites | The person uses Superpowers |
| CTX-S4 — `AGENTS.md` chain limit | The team also works with Codex, or the repository has `AGENTS.md` |
| CTX-P8 — monorepo with one fat root | Workspaces were detected |
| CMD-08 — fast test subset | A full test run takes longer than ~2 minutes by `run_command.py`; if not run: "not checked" |
| B3 — a task across several sessions | There are signs of tasks longer than one session |
| A vendor's ready-made skills (H3) | The vendor's dependency is in the manifest |

## What is never recommended

The "Never recommend" list in `SKILL.md`. A finding that leads to such a recommendation is discarded at
the recheck.
