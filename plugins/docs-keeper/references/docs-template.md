# Documentation template

One layout for every repository, whatever it builds. The names, places and order are fixed. What a
repository fills in depends on facts that can be checked: does it have a CLI, an API, a deployment,
releases.

## Contents

- [Layout](#layout)
- [Parts with a condition](#parts-with-a-condition)
- [The agent entry file](#the-agent-entry-file)
- [The index](#the-index)
- [Document classes](#document-classes)
- [Writing rules](#writing-rules)
- [Formats](#formats)
- [Quality criteria](#quality-criteria)

## Layout

| File | Needed when | Holds |
| --- | --- | --- |
| `README.md` | always | what this is, why and its status, quick start, links onward |
| `CLAUDE.md` | always | commands, non-obvious rules, traps; the index through `@docs/README.md` |
| `docs/README.md` | `docs/` exists | the index: each document and when to read it; then how to maintain the docs |
| `README.md` in a code folder | the repository has several top-level code folders | what is in the folder, where to start, a map of its modules, who owns it |
| `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md` | the project is public; a private one names an owner and a contact in the README | files, or README sections in a small project |
| `CHANGELOG.md` | the project has releases | changes users can see, `Unreleased` on top |
| `docs/architecture.md` | several deployable parts, or external systems it depends on | context, the main parts and how they talk; diagrams as text |
| `docs/<domain>.md` | a part of the code has states, rules or contracts spread over several files | one domain, in the sections of the domain page format; links for the rest |
| `docs/<area>/` | one area has two or more pages, such as billing: invoices and refunds | those pages; while the area has one page it is the file `docs/<area>.md`, and the folder appears in the change that splits it |
| `docs/<task>.md` | people repeat a task that is part of no single domain, such as setting up locally, running the tests, a release | the steps as commands to copy, and how to check it worked; a task inside one domain goes to "Changing it" on its domain page, and one only the agent carries out is a skill |
| `docs/decisions/NNNN-title.md` | a choice that is costly, risky or contested | one decision per file |
| `docs/reference/` | an outside interface has facts a person writes and no script can produce | those facts, looked up by row |
| `docs/generated/` | a script writes reference documents: CLI, configuration, schema, API | the script's output; never edited by hand |
| `docs/runbooks/` | the system is operated | one procedure per file, named after the symptom, each with an owner |
| `docs/glossary.md` | `docs/` exists | one for the whole project: a table of the term, what it means here, where in the code, the word not to use |
| `docs/tutorials/` | newcomers have to be taught | a first experience, step by step |
| nested `CLAUDE.md` | a top-level folder has its own stack and conventions; elsewhere, rarely: a directory has rules an agent would break on its first edit | that folder's conventions and traps, each rule with what to do instead; no documentation |
| `AGENTS.md` | other coding agents work in the repository | the shared text; `CLAUDE.md` then imports it with `@AGENTS.md` and adds what only Claude needs |

A small repository is complete with `README.md` and `CLAUDE.md`.

## Parts with a condition

- A part exists only when its condition holds and there is content for it. Never create an empty
  file, a heading with nothing under it, or a "TBD" section: a placeholder looks like documentation
  and tells the reader nothing.
- A part that does not apply is simply absent. An audit records it as "not applicable" with the
  reason; the repository gets no marker.
- Content that fits no row stays where it is and gets a line in the index. The layout is a place to
  find things, not a reason to delete them.
- Test a page by the need it serves: learning (tutorial), doing a task (a task page, a runbook),
  looking up a fact (reference), understanding why (architecture, a domain page, a decision). A page
  that serves two needs is usually two pages. A domain page is the exception: it explains one domain,
  holds the steps for its repeated changes, and links to the rest.

## The agent entry file

Nothing loads `docs/` by itself. An agent gets `CLAUDE.md` and finds the rest by path and by search,
so `CLAUDE.md` is a map, not a manual.

It holds, in this order:

1. **Commands**: install, test, lint, run, exactly as typed.
2. **Rules** the code does not show and a reviewer would insist on.
3. **Traps**: what looks right and is wrong here.
4. **Documentation**: `@docs/README.md`, which brings in the index and the rules for keeping the
   docs. Without `docs/`, a short table of exact path and "read when".

Keep it near 100 lines and under 200. The imported index loads with it, so keep the index short too.
A nested `CLAUDE.md` of a code folder stays under 300 lines. Leave out what the code already shows: an
architecture overview, a directory tree, a list of modules; a map of a folder's modules belongs in
that folder's README. A rule with no exceptions belongs in a hook or in CI, not in prose.

## The index

`docs/README.md` opens with a table of links. `CLAUDE.md` imports the whole file, so people and the
agent read one copy:

```markdown
| Document | Read it before |
| --- | --- |
| [architecture.md](architecture.md) | a change that spans several parts or adds an external system |
| [billing.md](billing.md) | changing how invoices are issued, retried or refunded |
| [decisions/](decisions/) | changing something a decision there settled |
```

After the table comes one section, "How to maintain the docs": which document to update for which
change, where new text goes, how to write, and a checklist before the merge request. Nothing else:
the file is always in the agent's context.

Every document under `docs/` is one step from this index. A document nothing points to will not be
found.

## Document classes

The class decides how a document may change.

| Class | Which documents | How it changes |
| --- | --- | --- |
| Generated | `docs/generated/`, or a first line that says a script wrote it | change the source and run the generator; never by hand |
| Record | decisions, released sections of the changelog | never rewritten: add a new entry, and change only the status of the old one |
| Living | everything else, `CLAUDE.md` and `README.md` included | edited in place, in the same change as the code |

Specs, plans and design docs have no class: they are working material for one change and stay out of
git. Their decisions go to `docs/decisions/`, and the behaviour they describe goes to its domain page.
Git keeps any file a repository deletes, so there is no archive folder.

## Writing rules

- **One fact, one place.** Other documents link to it. A copy goes stale the day the original
  changes.
- **Only what the code does not show.** Why, what must not be done, what will surprise. Do not
  restate code or a generated reference.
- **Names exactly as the code spells them**, in backticks: a reader and an agent find a document by
  searching for the name.
- **Commands and paths exactly as typed.** Every statement can be checked against the repository.
- **One topic per file**, named after what it holds. Under 500 lines; a table of contents past 100.
- **One term per concept.** No dates in prose, no "currently", "new", "temporary": they are false
  the next month.
- **Diagrams as text** (Mermaid or plain text), never only as an image.
- **Fixed section names on a domain page**, as the format below spells them, so a script can tell
  which sections exist. Subsections under them are free.
- **An invariant names its check**: the test, assertion or CI job that holds it. An invariant nothing
  checks is a wish, and the page says so.
- **The template applies when a document is touched.** A new document follows it from the first line.
  An existing one is brought in line in the section a change edits, never in a separate pass.
- **Write in the language the document already uses.**

## Formats

**Domain page** (`docs/<domain>.md`, or `docs/<area>/<topic>.md`; named after the domain as the code
names it). The sections come in this order. A section with a condition exists only when the code
meets it:

```markdown
# <The domain, as the code names it>

## Purpose
What it does, for whom, and what it deliberately does not do. One or two sentences.

## Where it lives
Its directories and two or three entry points, by exact name.

## Contracts
Who calls it and what it calls, one line each, with a link to the reference.

## Flows
One to three main scenarios, as steps or as Mermaid.

## Statuses
<!-- the code has a status enum, or a column with a fixed set of values -->
Each status as the code spells it, which ones are final, what moves an item between them, how it
fails and how it is cancelled.

## Queue and retries
<!-- the code has a queue consumer or a background job -->
Delivery, idempotency, the retry policy in words, where failed jobs end up. Numbers stay in settings.

## External services
<!-- the code has a client or an SDK of another service -->
For each one: the timeout, who retries, what happens while it is down.

## Model calls
<!-- the code imports an LLM SDK, names a model or keeps prompt files -->
Which model and where the prompts live, token and cost limits, how the output is checked, the evals,
the fallback, what data leaves.

## Settings
<!-- the code reads settings from the environment or a settings class -->
Which settings change behaviour and how they interact. Values live in the reference or the code.

## Invariants and traps
What must stay true, why, and the check that holds it. What looks right here and is wrong.

## Changing it
<!-- people repeat a change in this domain, such as adding a type or a provider -->
The steps for each repeated change.

## Operations
<!-- the domain runs in production: deploy files or alert rules exist -->
How to tell it works, its known failures, links to the runbooks.
```

Never on a domain page: lists of files or classes, signatures, copied values or defaults, a function
retold step by step, a list of terms of its own (they go to the glossary).

**Generated reference** (`docs/generated/<name>.md`): a script writes it, and a second run gives the
same file. The first line names the script and its source:
`<!-- Generated by scripts/gen_config_docs.py from app/settings.py. Do not edit. -->`. Typical ones:
`cli.md` from the CLI's `--help`, `config.md` from the settings class, `db-schema.md` from the
migrations, `api.md` from the OpenAPI file, `metrics.md` from the metrics registry. Text that an agent
or a model wrote is living, not generated: a second run would not give the same text.

**Decision** (`docs/decisions/NNNN-title.md`, numbered in order):

```markdown
# NNNN. <The decision as a phrase>

- Status: accepted | superseded by [NNNN](NNNN-title.md)
- Date: YYYY-MM-DD

## Context
What forced a choice. Facts, not the answer.

## Options considered
At least two real ones, each with what it costs.

## Decision
What was chosen, and why it beat the other options.

## Consequences
What gets easier, what gets harder, what is now ruled out: the bad ones too.
```

Status and date are list items so that they render on two lines. A decision that is replaced keeps
its text. Its status changes to `superseded by`, and the new decision says which one it replaces.

**Changelog**: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). New entries go under
`Unreleased`, grouped as Added, Changed, Deprecated, Removed, Fixed, Security. Written for a user of
the project, not as a list of commits.

**Runbook** (named after the symptom, such as `invoices-stuck-in-pending.md`): owner, when to use it,
steps as commands, how to check it worked, how to roll back.

**Glossary**: one file for the whole project. A domain page or an area folder keeps no list of terms
of its own: it uses the glossary's words. The file is a table sorted by term, with four columns: the
term; what it means in this project; where in the code it lives, as a link to a file or an enum with
no copy of its values; the word not to use for it.

## Quality criteria

Three questions, and who can answer each. There is no total score: a model's judgement varies from
run to run, so two scores cannot be compared.

| Question | Criterion | Checked by |
| --- | --- | --- |
| Is it right? | paths, commands and flags named in documents exist | script |
| Is it right? | nothing mentions code that was removed or renamed | script |
| Is it right? | versions, counts and lists match the manifests | script |
| Is it right? | each invariant on a domain page names a check that exists | script |
| Is it right? | the behaviour described matches the code | agent, with evidence |
| Is it right? | instruction files do not contradict each other | agent |
| Can it be found? | `README.md`, `CLAUDE.md` and the index of `docs/` exist, and `CLAUDE.md` imports the index | script |
| Can it be found? | no orphans: every document is reachable from an index | script |
| Can it be found? | relative links and anchors resolve | script |
| Can it be found? | each fact has one home | agent |
| Is it usable? | `CLAUDE.md` and each nested `CLAUDE.md` are within their line budgets | script |
| Is it usable? | no placeholders or empty sections; a long file has a table of contents | script |
| Is it usable? | a domain page has each section whose condition the code meets, under its fixed name | script finds the markers, agent confirms |
| Is it usable? | the README says what the project is for and its status | agent |
| Is it usable? | each part whose condition holds exists and has content | agent |
| Is it usable? | a decision names two real options and what the choice costs, and was not rewritten | agent |
| Is it usable? | clear, and written for its reader | judgement, reported as opinion |

`scan_docs.py` checks removed names, paths in backticks, links, anchors and orphans. The other rows
marked "script" have no script in this plugin yet: until one exists, the agent checks them.

A finding counts only when it harms a reader: a wrong statement, a blocked task, a contradiction.
Taste does not count. Staleness is measured by how much the code changed after the document was last
touched, not by the document's age: a stable document about stable code is not stale.
