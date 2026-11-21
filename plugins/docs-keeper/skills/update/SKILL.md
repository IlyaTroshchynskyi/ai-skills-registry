---
name: update
description: Brings a repository's documentation back in line with a finished code change. It finds every README, domain page, reference, CLAUDE.md, changelog and decision record the change touches, fixes what became false, and reports what it left alone. Use at the end of every development task that changed code or configuration, before saying the work is done and before a commit or a pull request, and whenever the user asks to update, sync or check the docs after a change, even if they do not name this skill. Not for writing documentation from scratch or reorganising it.
argument-hint: '[base ref to compare against, for example origin/main]'
allowed-tools: Bash(python3 -I ${CLAUDE_SKILL_DIR}/scripts/scan_docs.py *)
---

# Update the docs after a change

Documentation goes stale for one reason: whoever changed the code did not notice that the change
touched a document. You are at the one moment when the whole change is in view. Find every document
it made false, fix each with the smallest edit that makes it true, and say what you did.

Two facts set the bar:

- **Agents obey documents.** A stale command in `CLAUDE.md` gets run, not ignored. A false statement
  is worse than a missing one.
- **Filler is not free.** Text that restates the code or pads a changelog costs every later reader
  and buries the lines that matter. "Nothing to update" is a correct result, and often the right one.

## Rules

- **Documents only.** Do not change code, tests or configuration. Two exceptions: a generated
  document is refreshed by running its generator, and a file that only lists pages or settings for
  readers (a navigation file such as `mkdocs.yml` or `sidebars.js`, `.env.example`) gets the lines for
  the pages and settings the change touched.
- **Check against the code as it is now**, not against a summary of the change. Open the file before
  you write what it does.
- **Smallest true edit.** Fix the statement that became false. Do not rewrite the section, restyle
  it, reorder it or improve it while you are there: every extra line is something a reviewer has to
  read and nobody asked for.
- **Only what the code does not show.** What you add is something a reader cannot get from the
  code: why, a contract with the outside, an invariant, a trap, a step a person takes. Never a
  retelling of the code: what a function does step by step, lists of files or classes, values or
  defaults copied from it. A public flag, setting or route goes to the reference that owns such
  names; other documents link there.
- **An existing page before a new one.** Create a file only when the subject has no home anywhere.
- **Records are not stale.** A decision record, a released changelog section and an archived
  document say what was true then. A removed name inside them is history, not an error.
- **Never invent a reason.** Why a choice was made comes from the conversation, a commit message, a
  pull request or a comment in the code. If you cannot find it, ask, or leave it for a person.
- **Leave git alone.** Do not stage or commit unless the task you are finishing says to.
- **Language.** Write each document in the language it already uses. Talk to the user in the
  language of the conversation.

## Steps

### 1. Fix the scope

```bash
python3 -I ${CLAUDE_SKILL_DIR}/scripts/scan_docs.py impact
```

Add `--base <ref>` when the user gave one (`$ARGUMENTS`). Without it the script takes the branch
against the default branch, or else the uncommitted work, or else the last commit, and says which in
`scope`. If that is not the change you were asked about, pass the right base. Tell the user the scope
in one line. If the script answers with `error` instead, show it to the user and ask for the right ref.
Keep the `base_commit` it prints: step 7 needs it.

Then read the change itself: `git diff <base_commit>`, and the new files listed in `changed_code`.
The script reads names; only you read meaning.

If the folder is not a git repository, ask which files changed and work from them.

### 2. List what the change means to someone outside the code

Write down each change a user, an operator or another developer can observe, with the file and the
symbol it comes from, and the old and the new value where there is one.

| Counts | Does not count |
| --- | --- |
| a command, flag, option, endpoint or setting added, removed or renamed | a private function renamed or extracted |
| a default, a limit, a format or an error that behaves differently | a refactoring that keeps behaviour |
| a file, module or directory added, moved or removed | a bug fixed back to what the documents already say |
| how to install, build, test, run or deploy | a speed-up nobody can see from outside |
| a dependency or a service the project now needs or no longer needs | tests, formatting, comments |
| a choice that reverses or replaces an earlier decision | |

If the list is empty and the script found no stale mention, the result is "nothing to update": go to
step 8.

### 3. Find the documents

Use every source below. No single one is enough.

1. **`stale_mentions`** from the script: names that left the code and files that were removed or
   renamed, with each document line that still mentions them and the document's `kind`.
2. **`added_names_without_documents`**: new flags, settings and routes that no document mentions.
   These are hints. A public one needs a home in the reference; an internal one needs nothing.
3. **The project's own map**: a table in `CLAUDE.md` or `docs/README.md` that says which document
   to read for which part of the code.
4. **Your own search.** For every item in your list, search the documents for the names involved,
   including names that did not change. A default that went from 3 to 5 leaves every name in place,
   and the script reports nothing: only reading finds "retried up to 3 times". Search for the old
   value, the feature's name and the words a writer would have used.
5. **The table below**, as a list of places to look for each kind of change.

| What changed | Where to look |
| --- | --- |
| anything removed or renamed | every document that names it; the changelog |
| a setting, an option or a default | configuration reference, `.env.example`, quick start, `CLAUDE.md` |
| a public API, a command or a flag | reference (or the source it is generated from), task pages, examples |
| install, build or test commands | `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, task pages such as local development |
| a module or directory added, moved or removed | architecture, the folder's README, the domain page's "Where it lives", indexes |
| a domain's statuses, flow, contract, retries, model calls or invariants | its domain page, the section of that name |
| a dependency or required service | quick start, architecture, rules in `CLAUDE.md` that mention it |
| a choice that replaces an earlier decision | a new decision record; the old one marked superseded |
| deployment, rollback, alerts | runbook |
| anything a user of the project can see | `CHANGELOG.md`, under `Unreleased` |
| a page added, renamed or removed | the index, navigation, links that point to it |

Read each candidate passage in full, with the section around it. An example two paragraphs below the
sentence you came for is often false for the same reason.

### 4. Decide by the document's class

| Class | How to tell | What you do |
| --- | --- | --- |
| Generated | `kind: generated`: a `generated/` folder, or a first line saying a script wrote it | find the generator (the first line, `CLAUDE.md`, the build files) and run it. Never edit by hand. If you cannot find or run it, report that instead |
| Record | `kind: decision`, and released sections of a `kind: changelog` file | leave the text alone. A changelog gets a new entry under `Unreleased`. A decision that was replaced gets a new decision record, and only its own status line changes to "superseded by" |
| History | `kind: archive` | nothing |
| Living | `kind: living` and `kind: instructions` | edit in place |

For each affected document decide one of: fix a statement, remove a statement, add an entry, or
leave it, with the reason. A document that mentions the changed thing but says nothing false stays
as it is.

### 5. Edit

- Change the false statement and the examples that depend on it. Keep the document's own wording,
  structure and tone.
- A new fact goes into the one document that owns that kind of fact. Other documents link to it.
- On a domain page, a new fact goes under the section the template names for it. When you edit a
  section whose heading differs from the template's name, rename that heading; leave the sections you
  do not otherwise touch. An invariant you add or change names the test that holds it; if none does,
  write that nothing checks it and put it under "Needs a person".
- A changelog entry is one line for a user of the project: what changed for them and what they must
  do. Mark a breaking change as breaking. An internal change gets no entry.
- A new decision record follows the project's existing records and keeps every section they have.
  Fill each from what you can source: the diff, the conversation, the record it replaces. Keeping the
  old choice is always a real option, and the reason it was given up is its cost. What you cannot
  source, such as which other options were weighed, goes under "Needs a person" in the report: a
  dropped section makes the record look complete, and an invented option misleads whoever revisits
  the decision. If there are no records, or you need a new document of any kind, read
  `${CLAUDE_PLUGIN_ROOT}/references/docs-template.md` for where it goes and what it contains.
- Do not touch a "last updated" date in a document you did not otherwise change.

### 6. Indexes and links

When a page was added, renamed or removed: update the index (`docs/README.md`), the documentation
table in `CLAUDE.md` if it keeps one, any navigation file, and every link that pointed at the old
path. A page nothing points to will not be found.

### 7. Verify

```bash
python3 -I ${CLAUDE_SKILL_DIR}/scripts/scan_docs.py links --orphans <the documents you touched>
python3 -I ${CLAUDE_SKILL_DIR}/scripts/scan_docs.py impact --base <base_commit from step 1>
```

- `impact` gets the `base_commit` the first run printed: your own edits make the tree dirty, and
  without it the script would check only them.
- `links` must come back empty for the documents you touched, or you can say why not. A
  `not_a_document` entry means the path did not match a document: fix the path and run it again.
- In the second run, every remaining entry in `stale_mentions` is in a record or in history, or you
  can name the reason it stays.
- Read each edit once more against the code. Every command, path, name and number you wrote exists
  exactly as written.

### 8. Report

Keep it short. Use this shape, and leave out a part that is empty:

```markdown
Scope: <the scope, one line>

Updated
- `path`: what changed and which code change it follows

Left as is
- `path`: why (a record, history, still true)

Needs a person
- what you could not settle and what you need to know
```

When nothing needed changing, say so in one or two sentences with the reason, for example: "No
documentation changes: the diff renames a private helper and extracts a function; no document
mentions either, and behaviour is the same."

If the project's `CLAUDE.md` does not tell agents to run this skill before finishing a task, add one
line offering to put it there. Do not add it unasked.
