# Reference: documentation structure

## Contents

- 1. Four document types (Diátaxis)
- 2. What lives where
- 3. What NOT to propose as a separate document
- 4. ADRs: propose the practice
- 5. How documentation stays current
- 6. How to present a structure proposal in the report
- 7. Documentation rules
- Sources

Read this file when you go through group G of the checklist. Each documentation recommendation rests
on one of the rules below and explains "why" in its words, applied to this repository.

**"I work alone" does not cancel what the agent and the next developer need: ADRs, a glossary, a PR
template, `docs/README.md`.** The project may be handed over, and the agent reads these files in every
task. The answer cancels only what today only other people need: CODEOWNERS, onboarding pages,
how-tos and references for readers without an agent (step 6). The choice of a minimal structure does
not cancel them either: it cuts folders, not these artifacts.

## 1. Four document types (Diátaxis)

Diátaxis is this audit's own convention, neither confirmed nor refuted by the research sources. Call
it a convention in the report, not a standard.

Two questions determine the type: is the text about action or about knowledge? Is the reader learning
or working?

| Type        | Reader's question     | Form                                            | Sign of mixing                       |
| ----------- | --------------------- | ----------------------------------------------- | ------------------------------------ |
| Tutorial    | "Teach me"            | A lesson from zero to a result, read in full    | Reference tables in the middle       |
| How-to      | "How do I do X"       | Numbered steps to one goal, plus a check        | "Why it works" paragraphs between steps |
| Reference   | "How exactly is it"   | Tables and lists of facts, people look up a row | Reasoning and advice in a reference  |
| Explanation | "Why is it so"        | Design, reasons, constraints, alternatives      | Step-by-step instructions inside     |

**Why this matters.** A document that mixes types serves every reader badly at once: a newcomer
drowns in reference tables, an experienced reader cannot find the row among explanations. The more
types in one file, the faster it grows and goes stale. The exception is a document about one feature:
its design and a short reference can live together until the reference part grows.

## 2. What lives where

| Place                | What is inside                                         | How to name the file                  |
| -------------------- | ------------------------------------------------------ | ------------------------------------- |
| `README.md` (root)   | What this is, quick start, links onward                | —                                     |
| `README.md` in a folder | What is in the folder, which files to start with, who owns it | —                              |
| `docs/README.md`     | Table of contents "file — when to read"                | —                                     |
| `getting-started.md` | The only tutorial                                      | `tutorials/` from the second tutorial |
| `how-to/`            | One task, one file                                     | Verb + object: `add-x.md`             |
| `reference/`         | Facts that are not in the code or cannot be read there | Noun: `api.md`                        |
| `explanation/`       | Design and reasons; one complex feature, one file      | Topic: `authorization.md`             |
| `decisions/`         | ADRs                                                   | `NNNN-decision-as-a-phrase.md`        |
| `glossary.md`        | Domain and project terms                               | `docs/glossary.md`, unless one exists (G12) |
| `runbooks/`          | Symptom → diagnosis → action                           | Symptom: `backend-returns-5xx.md`     |
| `archive/`           | Implemented design docs and specs the person keeps (G5) | Date + topic                         |
| `generated/`         | References built by a script from the code             | Marked "generated, do not edit"       |

Rules:

- **Do not propose empty folders.** A folder appears together with a document. Why: an empty
  structure gives the reader nothing and creates the appearance of order.
- **Folders by type from the first document.** `how-to/`, `reference/` and `explanation/` appear as
  soon as the target structure has one document of that type: there is no flat `docs/`. With several
  subject areas or services, folders by area (`docs/<area>/…`) with the same type folders inside.
  `docs/README.md`, `docs/glossary.md` and `docs/decisions/` stay where they are in every case. Why:
  the path shows the type before the file is opened, and a folder added later means moving every file
  and fixing every link.
- **Folders that do not exist yet.** For each type the target structure has no document of, the report
  says in one line when to create its folder and why:
  - `how-to/` — with the first step-by-step instruction for one task: a reader with a task gets the
    steps without explanations in between;
  - `reference/` — with the first set of facts people look up by row (API, configuration, CLI): a
    reference without reasoning stays exact and quick to search;
  - `explanation/` — with the first document about design and reasons: reasons change rarely and are
    read once, so they do not crowd the documents used every day.
- **A glossary entry** has four parts: the term; what it means here; where in the code it lives — a
  file or an enum by link, with no copy of the values; which word not to use for it. Why: the agent
  names new code with the project's word instead of inventing a synonym, and a copy of enum values
  goes stale at the first change. When to propose the glossary: G12.
- **A README in each top-level code folder.** Why: a person opening the folder immediately sees what
  is in it, where to start and whom to ask. `CLAUDE.md` does not play this role: it is for the agent.
- **A table of contents with a "when to read" condition.** Why: both people and agents open a document
  only if they recognize their task in the link; a description of the content does not give that.

## 3. What NOT to propose as a separate document

| Do not propose                                                                  | Why                                                      | Instead                             |
| ------------------------------------------------------------------------------- | -------------------------------------------------------- | ----------------------------------- |
| A list of environment variables when a config schema and `.env.example` exist   | The schema is the reference; a copy goes stale           | A link to the schema file           |
| A hand-written DB schema when migrations exist                                  | It falls behind at the first migration                   | Generation from migrations or a link |
| An endpoint list that repeats the route definitions one to one                  | Two versions of one fact will diverge                    | A link or generation from schemas   |
| A how-to for a procedure a skill already describes, if only the agent does it   | A duplicate with no new reader                           | Keep it in the skill                |
| An ADR for a convention without alternatives                                    | Nobody will ask "why"; a line in `CLAUDE.md` is enough   | A line in the instructions          |
| Copies of code in documents                                                     | The copy goes stale, the original does not               | A `file:line` link                  |

Any new document in a recommendation names its **reader** and the **question** it answers, and
explains why the code and existing documents do not answer that question. No such reader, no
recommendation.

## 4. ADRs: propose the practice

An ADR (architecture decision record) records one decision that had real alternatives and
consequences. The test: if someone asks "why is it like this?" in six months, an ADR is needed. A
convention without alternatives is not one: a line in `CLAUDE.md` is enough (section 3).

**What ADRs give.** In the report, explain this in the project's words, on its example decision:

- the reason survives the people who knew it: without it a person or an agent either blindly
  preserves a decision that has become outdated, or "simplifies" it and breaks what it was made for;
- the agent reads the reason before changing the code the decision constrains, instead of guessing
  it from the code;
- the next developer learns why, not only what, without asking the author;
- a reversed decision stays in history: it is marked superseded and a new ADR is written, so nobody
  brings back a rejected option without knowing why it was rejected.

**What the audit does.** The audit took no part in the project's decisions and does not invent ADRs.
Two sources only:

- **decisions recorded in specs and design docs** are transferred into ADRs during the audit (below):
  the reason is already written down, and after a spec is deleted it is gone;
- **every other decision** is written by the people who make it, starting with the first decision
  after the audit.

**Always.** The practice is proposed in every report that covers area G; answers about readers
("I work alone") and the choice of a minimal structure do not cancel it. If the project has no ADR
practice:

1. the folder `docs/decisions/`, its own even in a small project: ADRs have
   continuous numbering and statuses (accepted, superseded by NNNN);
2. the template `docs/decisions/0000-template.md`, the text below;
3. a line in the root `CLAUDE.md`: "a decision with alternatives gets an ADR in `docs/decisions/` in
   the same MR";
4. one example ADR on a real decision of this project, so the format is seen on familiar material
   (choosing it: below), unless an ADR transferred from a spec already covers that decision. If no
   such decision is found, the template alone.

If the project already keeps ADRs (`doc/adr/`, `docs/adr/`, `docs/architecture/decisions/`): no new
folder, new ones go there and continue its numbering; check the format (CTX-D3) and whether the root
`CLAUDE.md` has the line.

**Choosing the example.** The most architecturally significant decision the repository shows: one that
is expensive to reverse and constrains later decisions.

- storage: a document store or a relational DB; the choice of a vector store;
- the main framework: Django or FastAPI, an agent framework or a hand-written loop;
- the execution model: a single process, async end to end;
- the protocol: SSE or WebSocket;
- an own implementation instead of a ready one, for example an own job queue instead of a library.

The test: "if this changes, how much code and data must be redone?" and "which later decisions were
made because of it?". Signals:

- dependencies in the manifest, for example a NoSQL client without an SQL driver;
- services in `docker-compose`;
- documents that compare options, for example two schema drafts for the same data;
- prohibitions in the instructions ("run as a single process");
- an own class on top of a library interface;
- a "Decision Record" or "Alternatives" section in a design doc.

The example contains only what the repository says, with `file:line`. What it does not say — why this
option, which alternatives were considered — stays a placeholder for the person:
`<why this option: fill in>`. The audit does not guess reasons and does not ask for them: the person
fills them in after the audit.

**Transferring decisions from specs.** Every design doc and spec, kept or about to be deleted (G5):
sections "Decision Record", "Alternatives", "Considered and Rejected", "Why …" and any choice between
named options. Each decision with real alternatives becomes one ADR in full, in the template below:

- status "accepted" if the spec is implemented; the date is the spec's date;
- Context, Decision and Consequences are the spec's words, shortened to 1–3 sentences each; the
  rejected options are named as the spec names them;
- the ADR stands on its own: the spec may be deleted, so a link to it is only an addition
  (`Source: <path>, section <name>`) and only for a spec that is kept or archived;
- numbering in the order the decisions were made, after the project's last ADR.

What the spec does not say is not added: no guessed reasons, no alternatives it does not name.

### ADR template

Nygard's format: title, status, context, decision, consequences — all of them, not only the good
ones. A reversed ADR is not deleted: it gets "superseded by NNNN" and a new one is written.

```markdown
# NNNN. <Decision as a phrase>

- Status: accepted <!-- proposed | accepted | superseded by NNNN -->
- Date: <YYYY-MM-DD>

## Context

<!-- What forced a decision and which options were on the table. -->

## Decision

We will <…>.

## Consequences

<!-- What becomes easier, what becomes harder, what must not be done now. -->
```

## 5. How documentation stays current

- **Docs in the same MR as the code.** Check whether there is an item in the MR template or a rule in
  the instructions.
- **Generation instead of a hand-written reference**, plus a CI check that the generated output
  matches the source.
- **Link and path checks in CI.** Usually a new tool: "Needs approval".
- **An owner** for each section: in the folder README or in CODEOWNERS.
- **A "keep or delete" cleanup.** Delete what is definitely wrong first; the default is to delete, git
  remembers everything.
- **Do not write what will certainly change into docs:** file counts, versions, full lists of CI jobs.

Signs of staleness to look for: the document itself says it has fallen behind ("predates", "outdated",
"lags"); numbers and versions do not match reality; mentioned paths do not exist; a design doc or spec
sits next to current documentation as an equal.

## 6. How to present a structure proposal in the report

- A target tree: existing content, to the right of each file where the text comes from
  (`← README.md: API Reference`), plus the new documents of G5, G6, G7 and G12 marked "new"; other new
  files only with a justification from section 3.
- One line: which structure was chosen (folders by type, folders by area) and the sign that decided
  it (section 2).
- After the tree, a Mermaid diagram is mandatory: it renders on GitHub and in IDEs. The example is in
  `report-template.md`.
  - **Nodes** are the documents of the target structure, within the G10 node threshold
    (`references/thresholds.md`); past that, one node for a group of files (`docs/how-to/*`).
  - **Groups** (`subgraph`) are loading classes: "Always in context" — the root `CLAUDE.md`; "On
    demand" — nested `CLAUDE.md`, rules with `paths`, skills; "Reference" — `README.md`, `docs/`;
    "Decisions" — `docs/decisions/`.
  - **Arrows** show where an agent or a person comes to the document from: `README.md` →
    `docs/how-to/run-locally.md`, the root `CLAUDE.md` → a nested one.
  - **Colour** (`classDef`) marks a new, a moved and an unchanged document; unchanged ones may keep the
    default style. Documents being deleted are not on the diagram: they are listed in "What
    disappears".
- The folders that do not exist yet: one line each, when to create it and why (section 2).
- Separately: what disappears entirely and why.
- Order of work: small MRs, one document at a time; when moving, update links in `CLAUDE.md` and other
  docs in the same MR.
- Analyze by headings and by text. If you compared only headings, say so with the label "compared by
  headings": the text gets compared during the move.

## 7. Documentation rules

A structure holds only if it is written down when, what and where to write. Why this matters: without
such rules an agent updates whichever document it happens to see or creates a new one next to the old
one, and a person does not understand why a document sits where it does and stops trusting the
structure.

The rules are complete if they answer four questions:

| Question            | What must be written                                                                                       |
| ------------------- | ---------------------------------------------------------------------------------------------------------- |
| When to update      | "In the same MR as the code", plus a "what changed → which document → why" table                           |
| Where to put new things | Decision order: can it come from the code → who is the reader → type → does a document exist → a line in the table of contents |
| How to write        | The point in the first sentence, links instead of code copies, no numbers that go stale, one fact in one place |
| How to check        | A pre-MR checklist                                                                                         |

Where the rules should live and how each reader reaches them:

| Who                       | Where                                                                      | Why                                                       |
| ------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------- |
| A person                  | A "How to maintain documentation" section in `docs/README.md`; an item in the MR template | The entry to the documentation; a reminder at MR time |
| An agent changing code    | One line in the root `CLAUDE.md` linking to the section                    | The root file always loads and survives compaction        |
| An agent editing docs     | `.claude/rules/docs.md` with `paths` on `docs/**/*.md` and `**/README.md`  | An addition: loads when working with docs, gone after compaction |

The full text of the rules lives only in `docs/README.md`. `CLAUDE.md` and the rule link to it and
repeat at most the three most important items: two full copies will diverge. The rule and the MR
template must be in git.

If there are no rules or they are incomplete, the report gets a draft section for this repository. The
"what changed → which document" table includes only rows for documents that exist in the project or
are proposed in the target structure; the path in each row is real. Plus ready texts for the
`CLAUDE.md` line and the `docs.md` rule. The PR/MR template goes into the report in any case, see
below.

### PR/MR template

**Why.** The template serves not the reader of the documentation but three others:

- the agent writing a PR description. Without a template it decides each time what to write and skips
  "how it was verified". With `gh pr create --body` the template is not filled in by itself, so a line
  in `CLAUDE.md` is needed;
- the next developer: the PR history is the only place that shows what changed and why;
- the history of decisions when specs are one-off: the spec is deleted, but the PR description with
  the acceptance criteria and the verification result stays.

**When to propose.** Always, when the repository has a remote (`git remote -v`). In the report write
only the host (`github.com`, `gitlab.example.com`), never the full URL: it can contain a token
(`https://oauth2:<token>@…`). A self-hosted GitLab has its own domain: `.gitlab-ci.yml` or `.gitlab/`
in the repository is the sign. For a host other than GitHub or GitLab, give the same text and say that
the host's documentation decides the path. Team size and answers about readers do not cancel it. If a
template exists, check it against the content below instead.

**Path:** GitHub — `.github/pull_request_template.md`; GitLab —
`.gitlab/merge_request_templates/Default.md`. The file must be in git: check with `git check-ignore`.
Look for an existing template in any case and folder first:
`git ls-files | grep -iE 'pull_request_template|merge_request_templates/'`.

**Content.** Short, up to ~15 lines, fitted to this project. The items come from the repository: its
verification command, its "Ask first" list, its place for ADRs. Checkboxes only for what can be
checked. An example for a project where specs are one-off, `make check` verifies everything and
`CLAUDE.md` has an "Ask first" list:

```markdown
## What and why

<!-- 1–3 sentences. -->

## Task

<!-- Acceptance criteria as given (specs here are one-off, so they live on in this PR),
     or a link to the issue. -->

## Decisions

<!-- docs/decisions/NNNN-… if a choice between real alternatives was made, otherwise "none". -->

## Verified

- [ ] `make check` passes
- [ ] Checked in the running app: <what>, or "not needed"

## Needs attention

<!-- Anything from "Ask first" in CLAUDE.md this touches: a paid external call, a public API
     contract changed (link to the client PR), stored data changed. Otherwise "none". -->

## Docs

<!-- Which documents changed, or "none needed". -->
```

**Line in the root `CLAUDE.md`:** "A PR description fills `.github/pull_request_template.md`." For
GitLab: "An MR description fills `.gitlab/merge_request_templates/Default.md`." For another host: the
same line with the path that host uses.

## Sources

Diátaxis (diataxis.fr), Google Documentation Best Practices and READMEs
(google.github.io/styleguide/docguide), Michael Nygard "Documenting Architecture Decisions", AGENTS.md
(agents.md), Claude Code best practices, HumanLayer "Writing a good CLAUDE.md".
