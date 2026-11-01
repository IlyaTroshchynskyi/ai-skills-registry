# Module J. Built-in diagnostics and usage history

## Contents

- `/skill-doctor`
- `/doctor prompt-audit`
- `/doctor`
- `/insights` data

Claude Code's built-in commands already do part of the audit. This module says how to get their data,
what to take from it and how to connect it to our own checks. The audit's own value is in the
connections no single command makes. Example: "30 `Command Failed` in the project's sessions" plus "no
verification command in `CLAUDE.md`" is one recommendation in group C.

Findings are labeled with their source: `[skill-doctor]`, `[prompt-audit]`, `[doctor]`, `[insights]`.
Findings about the person's personal setup (`~/.claude`, synced skills, installs) are labeled
"personal".

## `/skill-doctor`

- **Run:** `claude -p "/skill-doctor" --permission-mode plan`. No separate consent is needed: the
  command changes nothing and answers quickly.
- **What it gives:** for each skill in the listing, its source, cost in context, tokens over 7 days,
  number of invocations, last invocation; lists "loaded but never invoked" and "plugins unused for a
  long time".
- **Where it goes:** F2 in `checklist.md`, SK-18 and SK-14 in `modules/skills.md`, H5 (how many times
  methodology skills were invoked).
- **Labels:** machine-level data, not repository-level. Project skills from `.claude/skills/` are "in
  repo", the rest are "personal".

## `/doctor prompt-audit`

The most valuable built-in for the audit: it works at the repository level.

**A ready report.** A run is expensive: in an audit of a single area it took about 40 % of the tokens.
Before asking for consent, look for a ready report for this repository:
`python3 -I <skill dir>/scripts/find_prompt_audit_plan.py --max-age-days 7 --repo <repository path>`.
If one is found, offer it in the consent message instead of a new run, with its date (`date -r <path>`).
If the instructions changed after that date (`git log -1 --format=%cI -- <instruction files>`,
`git status --short`), say so in the same item. When you use a ready report, say in the audit report
header: "ready prompt-audit report from <date>".

**Run**, only with consent (minutes of work and tokens):

1. Remember the time: `date +%s`.
2. Run `claude -p "/doctor prompt-audit <repository path>" --permission-mode plan` in the background
   (Bash with `run_in_background`): it takes minutes and will not fit in the Bash tool timeout. Wait
   for the completion notice. In plan mode it changes nothing.
3. Find the full report: `python3 -I <skill dir>/scripts/find_prompt_audit_plan.py --since <time from
   step 1> --repo <repository path>`. The script returns the path to `~/.claude/plans/prompt-audit-*.md`
   created after the run. Exit 1 means no report: use the text the command printed; if there is none
   either, `check_refs.py` already checked paths and commands at step 2, the rest is "not checked".
4. Read the findings table: location, quote, pattern, confidence, action.

**What goes where:**

| `prompt-audit` finding | Audit item |
| --- | --- |
| Link to a nonexistent file | A4 |
| Wrong version or fact | A5 |
| Contradiction between files | A6 |
| Nonexistent command | C3 |
| Wording aimed at old models, caps, numeric output limits | CTX-C11 |
| Dead link inside a skill | H1 in `modules/skills.md` |

- **What to discard:** findings about the application's own prompts and tool descriptions (the groups
  "Tool descriptions", "API request setup", prompts in the application code): that is not the harness.
- **Low confidence:** findings marked "flag" do not go to recommendations, only to "Open questions".
- **If `prompt-audit` is not allowed:** `check_refs.py` checks paths and commands (`checklist.md`, A4
  and C3), and contradictions and outdated wording are "not checked — no consent".
- **Side effect:** the command writes a plan file to `~/.claude/plans/`. Mention it in the report
  header ("what ran").

## `/doctor`

**Run by the user, not by the skill.** In the background it behaves inconsistently: access to settings
comes and goes, and recommendations on the same data diverged. Ask once per audit: "Please run
`/doctor` in your session and pass me the output or the path to the plan file it saves." No output:
"not checked".

What to take:

- **Repository level:**
  - derivable content of `CLAUDE.md` (CTX-C3), to "What to remove";
  - this project's hook timings (HK-07);
  - auto memory that duplicates `CLAUDE.md` (CTX-D2);
  - old worktrees (E3).
- **Personal setup, labeled "personal":**
  - unused synced skills, agents and plugins (F2, SK-18);
  - leftovers of old Claude Code installs.

`/doctor`'s advice to enable auto mode does not carry over to the report: auto mode is on the "Never
recommend" list.

## `/insights` data

**Is there history.** Before the consent message, check presence only, without reading content:

- directories in `~/.claude/projects/` whose name starts with the repository path with all characters
  except letters and digits replaced by hyphens (`/home/u/my_app` → `-home-u-my-app`; worktrees and
  subdirectories give names with the same start);
- the directory `~/.claude/usage-data/session-meta/`.

If either is missing, there is no history: leave the item out of the consent message and skip the step.

**Run**, with consent: `python3 -I <skill dir>/scripts/insights_summary.py <repository path>`. Sessions
from the repository's subdirectories and worktrees count; neighboring directories with a similar name
do not.

| `status` | What to do |
| --- | --- |
| `ok` | Use the data |
| `stale` | Use it with the label "data older than 30 days" and suggest the person run `/insights` to refresh it |
| `no_data` | No sessions for this project: skip the step, one line in the report |
| `unexpected_format` | The file format changed: "not checked" |

What to take:

| Field | Signal | Where |
| --- | --- | --- |
| `tool_error_categories`: many `Command Failed` | Commands fail: no working verification command, wrong commands in the instructions | Group C, A4/C3 |
| `bash_would_prompt_count` | Many permission prompts for routine project commands | PRM-09: allow rules for the project's own lint/test/build (not auto mode) |
| `friction_counts`: `wrong_approach`, `misunderstood_request` | The agent lacks project knowledge | Group A, H2, D5 |
| `friction_details` | A description of friction is evidence | H2: new skill candidates; D5 |
| `user_interruptions` | The person often stops the agent | Context for A and K |

Paraphrase `friction_details` in your own words in the report, without quotes or personal details: the
report may be shown to the team. In the evidence give numbers and the window: "over 32 project
sessions (2026-09-16 to 2026-10-10): `Command Failed` — 33". The file format is not documented by
Anthropic and may change.
