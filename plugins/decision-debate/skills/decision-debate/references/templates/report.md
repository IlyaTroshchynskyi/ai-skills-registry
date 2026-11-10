# <Title: the task, in a few words>

Report NNNN · YYYY-MM-DD · Status: proposed | chosen: <option> | parked

## In short

- **Recommended:** <the solution in one or two plain sentences>.
- **Why:** <the one or two reasons that decide it>.
- **What it costs:** <what we give up, in plain words>.
- **Not ready yet:** <open problems from the review, or "nothing">.
- **Assumed without asking:** <only with `--unattended`: each fork that took its default, one line each;
  otherwise leave this line out>.

## Decision

Chosen: <option>, by <user>, because <reason>. Given up: <what>.

Before the user has chosen, list instead the 1–3 questions whose answers pick the option, each with
where each answer leads ("No → O2").

## Options

| | How it works | Pros | Cons | Choose it if |
| --- | --- | --- | --- | --- |
| **O1** <name> | <a few words> | <a few words> | <a few words> | <a few words> |

One line on relative effort (O1 < O2 < O3), and one line on options rejected early, with the reason.

## Easy to miss

4–7 points, each in this shape: **the trap, in bold**, then what the solution does about it.

## How it works

The chosen option in 5–8 numbered steps, from the user's action to the stored result and back. Then one
short paragraph: how it is switched on and how it is undone.

## Key decisions

| Decision | Chosen | Instead of | Why |
| --- | --- | --- | --- |

Up to 5 rows: the choices inside the solution that are hard to reverse or that a reader would question.

## Risks and open issues

Up to 5 points: the risk in plain words, what handles it, and what is still open. Unresolved review
findings and the proposal's open questions for the user go here, described, not numbered.

## Plan

1. <a milestone with a result you can check>

4–8 milestones. End with: the detailed plan by file is made after the choice, against the code.

## Revisit if

2–4 observations, one line each, that would make another option the better choice.

## More detail

- Full design of the chosen option: `NNNN-<slug>/proposal-vN.md`
- Review and verification: `NNNN-<slug>/critique-r*.md`, `NNNN-<slug>/verification-r*.md`
- Research and sources: `NNNN-<slug>/research/`
- How it was checked: N review rounds; serious findings: N confirmed, N refuted, N open.
