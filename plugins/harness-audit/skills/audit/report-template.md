# Report template

## Contents

Report sections in order: Top recommendations; Summary; Recommendations; Skills; What to remove; Checked and fine; Documentation: target structure; Fresh-session test; Commands run; Open questions; Not checked.

File: `harness-audit-<YYYY-MM-DD>.md` in the root of the audited repository. Write the report in the
language of the conversation and translate the section names. Do not delete empty sections: write
"none". Sections in order:

````markdown
# Harness audit — <repository> — <date>

Branch <branch>, commit <sha>. Areas: <all / named>. Claude Code <version>, criteria: 2026-10-17.
What ran: <commands, prompt-audit, /skill-doctor, insights_summary.py; files left in
~/.claude/plans/>. No consent for: <items>.

## Top recommendations

Up to 5 recommendations to start with, from any area, by effect on the person: one line each and a
link to its detailed item below. On a tidy project there may be fewer or none: do not pad to the number.

## Summary

| Area | State | Main gap |
| --- | --- | --- |
| A. Instructions | | |
| B. Spec to code | | |
| C. Verification | | |
| D. Review | | |
| E. Environment | | |
| F. Hygiene | | |
| G. Documentation | | |
| H. Skills | | |
| I. Mechanisms | | |
| J. History | | |
| K. Design before code | | |

Areas that do not apply get a line "not applicable: <why>". There is no overall score.

## Recommendations

### Quick

#### 1. <what to do>

- **Problem:** `path:line` — one sentence. Check ID.
- **Evidence:** what you saw: a quote, a number, command output, session data.
- **Why it matters:** what this breaks in the agent's work; a link to the source.
- **Change:** the file and a snippet; a hook or script in full.
- **Size:** S / M / L.
- **Where:** in repo / personal.
- **Source:** [own analysis] / [prompt-audit] / [doctor] / [skill-doctor] / [insights].

### Medium

### Needs approval

## Skills

### Create

Name, task, evidence, ready `description`, who invokes it, a description in 5–10 sentences, how to
verify. Made later with `skill-creator`.

### Improve

### Install

Source and its tier, the need or a dependency from the manifest, what changes for you, cost in
context, security check, command.

### Worth a look

Popular third-party repositories, up to 5: link, stars, days since the last change, license, why it
fits (need or stack), what changes for you. State that no full security check was done. No install
command.

### Disable

## What to remove

Content derivable from code in `CLAUDE.md`, rules a linter or hook duplicates, unused skills, agents,
plugins, MCP servers: with evidence and the label "in repo" / "personal".

## Checked and fine

ID — one line of evidence.

## Documentation: target structure

| Document | Diátaxis type (convention) | Problem | What to do and why |
| --- | --- | --- | --- |

    <target tree; to the right of each file, where the text comes from: ← README.md: API Reference>

What disappears entirely and why. Proposed ADRs: title, alternatives and where it came from
(`file:line` or the person's answer). If there is no ADR practice, how to start one.

### Documentation rules

Whether they exist and where. If they are missing or incomplete, a draft "How to maintain
documentation" section for `docs/README.md` with this repository's real paths, and the texts for
`CLAUDE.md`, the rule and the MR template.

## Fresh-session test

| Question | Subagent's answer | Source | Correct? |
| --- | --- | --- | --- |

## Commands run

| Command | Time, s | Exit code | Output lines / bytes | Timeout |
| --- | --- | --- | --- | --- |

## Open questions

Unanswered questions and the recommendations that depend on them; low-confidence `prompt-audit`
findings.

## Not checked

Item — reason: no consent ("not checked — no consent"), no evidence, no data.
````
