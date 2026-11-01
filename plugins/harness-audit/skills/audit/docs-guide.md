# Reference: documentation structure

## Contents

- 1. Four document types (Diátaxis)
- 2. What lives where
- 3. What NOT to propose as a separate document
- 4. When an ADR is needed
- 5. How documentation stays current
- 6. How to present a structure proposal in the report
- 7. Documentation rules
- Sources

Read this file when you go through group G of the checklist. Each documentation recommendation rests
on one of the rules below and explains "why" in its words, applied to this repository.

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
| `runbooks/`          | Symptom → diagnosis → action                           | Symptom: `backend-returns-5xx.md`     |
| `archive/`           | Design docs and specs after implementation             | Date + topic                          |
| `generated/`         | References built by a script from the code             | Marked "generated, do not edit"       |

Rules:

- **Do not propose empty folders.** A folder appears together with a document. A flat `docs/` is fine
  in a small project if the type is clear from the file name. Why: an empty structure gives the reader
  nothing and creates the appearance of order.
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

## 4. When an ADR is needed

An ADR is for a decision that had real alternatives and consequences and that someone will want to
revisit. The test: if someone asks "why is it like this?" in six months, an ADR is needed. Why this
matters: without a recorded reason, a person or agent either blindly preserves a decision that has
become outdated, or "simplifies" it and breaks what it was made for.

Signals of a candidate in code and documents:

- `version` / `expectedVersion` fields, 409 responses, retries: optimistic locking;
- locks with a timeout, leases, keepalive;
- a foreign key with `RESTRICT` together with a check in a service;
- a non-standard pattern with a "do not change" warning in the instructions;
- a dispute in review reports or an MR after which one option was chosen;
- a "Decision Record" section inside a design doc.

Where to get candidates, in order:

1. **Design docs and specs**: sections "Decision Record", "Alternatives", "Considered and Rejected",
   "Why …". Especially those the person is about to delete: after deletion the reason is gone.
2. **Existing documentation** that explains "why". An ADR briefly records the decision and alternatives
   and links to the document; the document stays.
3. **Signals in the code**: the list above.
4. **The person**, if nothing turned up: "which decisions did you choose from several options?".

Nygard's format: title, context, decision ("We will…"), status, consequences — all of them, not only
the good ones. A reversed ADR is not deleted: it is marked superseded and a new one is written. In the
report, propose 1–3 candidates with a source (`file:line` or the person's answer), not a list of
hypothetical ones.

If the project has no ADR practice, propose keeping ADRs even if no candidates turned up: a
`docs/decisions/` directory, Nygard's template and a line in `CLAUDE.md`: "a decision with
alternatives gets an ADR in the same MR".

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

- A target tree of existing content only: to the right of each file, where the text comes from
  (`← README.md: API Reference`). New files only with a justification from section 3.
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
`CLAUDE.md` line, the `docs.md` rule and the MR template item.

## Sources

Diátaxis (diataxis.fr), Google Documentation Best Practices and READMEs
(google.github.io/styleguide/docguide), Michael Nygard "Documenting Architecture Decisions", AGENTS.md
(agents.md), Claude Code best practices, HumanLayer "Writing a good CLAUDE.md".
