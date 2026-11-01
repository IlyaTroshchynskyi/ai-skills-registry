# Module K. Design before code

The module's question: does the person discuss decisions and tasks with the agent before the agent
writes code? This can be a spec-driven framework (Superpowers, Spec Kit, OpenSpec, BMAD, Kiro) or their
own skills and agents for brainstorming and specs. The module is not tied to a specific framework: any
works, including a home-grown one.

Implementation plans are neither checked nor recommended (the "Never recommend" list in `SKILL.md`).

## How to identify the tool

The practice is identified by the person's tools, not by artifacts in the repository. Missing spec
files prove nothing: developers delete them.

Signs, strongest first:

1. **Installed plugins:** `claude plugin list --json` (the `installed` field): `superpowers` and other
   methodology plugins.
2. **Invocation history:** `/skill-doctor`: how many times skills like `superpowers:brainstorming` were
   invoked.
3. **Skills, commands and agents of the person and project** (inventory) with brainstorming, spec,
   design or requirements in the name or `description`.
4. **Traces in the repository:**
   - `docs/superpowers/specs/` — Superpowers;
   - `.specify/`, `memory/constitution.md` — Spec Kit;
   - `openspec/` — OpenSpec;
   - `_bmad/` or `.bmad-core/` — BMAD;
   - `.kiro/specs/` — Kiro;
   - `specs/` directories and design docs.

## If a tool exists

Check whether the project is ready for it. Common prerequisites of any spec-driven process:

- **SP-04. A clean test baseline.** The test command on a clean checkout exits with code 0 and no
  warnings; otherwise every later failure is ambiguous. Checked by running it (C8 in `checklist.md`,
  after consent).
- **SP-05. A working, targeted and fast test command.** One file or test can be run (CMD-07), and the
  full suite is not too long. Without this, "run it, it should fail / pass" steps cannot be verified,
  and a slow suite multiplies the cost of every task.
- **SP-07. A place for specs under version control.** If specs are kept, the path is set in the
  instructions imperatively and concretely. A soft wish ("specs are better placed in…") loses to a path
  hard-coded in the framework's skill. If specs are disposable, that is written down (B1).

Only for Superpowers:

- **SP-09. Version.** The installed version against the marketplace version (`claude plugin list --json
  --available`); installs of different versions at user and project level. An outdated install is
  "personal".

The other prerequisites (SP-01…SP-03, SP-06, SP-08, SP-10…SP-12) come after calibration. Duplicate
methodology skills are H5 in `modules/skills.md` (SP-13).

## If there is no tool

This is a recommendation, not tied to a specific framework: set up a way to discuss decisions and tasks
with the agent before code.

- **Evidence:** friction from the history (`wrong_approach`, `misunderstood_request`,
  `excessive_changes` in `insights_summary.py`), large changes with no trace of discussion, repeated
  rework.
- **Options:** the brainstorming skill from Superpowers, Spec Kit, OpenSpec or a home-grown skill for
  discussing decisions. The choice is the person's; each option costs time and tokens on every task.
- **Label:** installing a framework is "personal"; spec conventions in the project instructions are "in
  repo".

Ideas from other frameworks that can be proposed without changing tools, only with evidence of need:

- **A short section of project principles** in the instruction file: stack, non-negotiable rules
  (constitution in Spec Kit, steering in Kiro).
- **Structured acceptance criteria** ("SHALL" plus "GIVEN / WHEN / THEN" scenarios, as in OpenSpec),
  connected to B2.
- **A bugfix spec template:** current, expected and unchanged behavior (Kiro).
