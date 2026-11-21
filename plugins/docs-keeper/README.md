# docs-keeper

A Claude Code plugin that keeps a repository's documentation true. At the end of a development task
it reads the change, finds every document the change touched, fixes what became false with the
smallest edit, and reports what it left alone. When nothing needs changing it says so and changes
nothing.

It works on any project and any layout. It also carries one documentation template, the same for
every kind of repository, which the skill uses when a new document needs a place.

## Install

```bash
claude plugin marketplace add IlyaTroshchynskyi/ai-skills-registry
claude plugin install docs-keeper@troshchynskyi-plugins
```

Requires Python 3.10 or later and git.

## Use

Claude starts the skill by itself when a task that changed code is finished. You can also run it:

```text
/docs-keeper:update
/docs-keeper:update origin/main
```

Without an argument it takes the branch against the default branch, or else the uncommitted work, or
else the last commit, and tells you which. The argument is a base ref to compare against.

### Make sure it runs

A skill that is only described gets skipped often. Add one line to the project's `CLAUDE.md`:

```markdown
Before you report a task as done, run the `docs-keeper:update` skill.
```

The skill offers this line once when it is missing, and never adds it without your yes.

## What it does

1. Fixes the scope of the change and reads the diff.
2. Lists what the change means to someone outside the code: a renamed setting, a new default, a
   removed flag, a replaced dependency. A refactoring that keeps behaviour is not on the list.
3. Finds the documents: a script reports names that left the code and files that were removed or
   renamed, with every document line that still mentions them. The skill then searches by meaning,
   because a default that changed leaves every name in place.
4. Treats each document by its class.

| Class | Examples | What happens |
| --- | --- | --- |
| Generated | `docs/generated/`, a file whose first line names its script | the generator is run; never edited by hand |
| Record | decision records, released changelog sections | left as written; a new entry or a new record is added |
| History | an archive folder a repository already keeps | nothing |
| Living | README, domain and task pages, reference, `CLAUDE.md` | edited in place |

5. Updates indexes and links, checks links and paths in what it touched, and reports: updated, left
   as is, needs a person.

## What it does and does not touch

- It edits documentation only. It does not change code, tests or configuration, and it does not stage
  or commit.
- It runs a generator only to refresh a generated document that the change made stale.
- It never invents the reason for a decision. If the reason is not in the conversation, a commit or
  the code, it asks or leaves the record for you.
- It writes each document in the language that document already uses, and talks to you in yours.

## The template

[references/docs-template.md](references/docs-template.md) is the layout the plugin assumes: a small
required core (`README.md`, `CLAUDE.md` as the agent's map, an index in `docs/` that `CLAUDE.md`
imports), parts that exist only when a condition holds (an API, a deployment, releases, a domain with
statuses or retries), a domain page with fixed section names, document classes, writing rules and
quality criteria. No part is created empty.

## Why it works this way

- Documents go stale because the author of a change does not notice it touched them: 28.9% of the
  1,000 most popular GitHub projects reference code that no longer exists, and such references live
  4.7 years on average ([Tan et al.](https://arxiv.org/abs/2212.01479)). So the check runs at the
  moment of the change, from the diff.
- Agents follow what instruction files say, and generated context files raise cost without raising
  success ([ETH Zurich](https://arxiv.org/abs/2602.11988)). So the skill removes false
  statements first and adds as little as it can.
- An agent used a documentation skill in under half of the cases where it applied, and almost always
  once an instruction file said to
  ([Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)). So the README
  asks for one line in `CLAUDE.md`.
- Change the document in the same change as the code, keep the set small, delete what is dead, do
  not duplicate ([Google](https://google.github.io/styleguide/docguide/best_practices.html)).
- A domain page explains one part of the code and holds the steps for its repeated changes, as
  GitLab's documentation does for a feature
  ([GitLab](https://docs.gitlab.com/development/documentation/topic_types/)). What developers most
  often cannot recover is why the code is the way it is, not where it lives
  ([LaToza et al.](https://www.st.cs.uni-saarland.de/edu/empirical-se/2006/PDFs/latoza06.pdf)). So
  the page holds invariants and reasons, under fixed section names a script can check.
- A decision record is kept and marked superseded, not rewritten
  ([Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)); changelog
  entries go under `Unreleased` ([Keep a Changelog](https://keepachangelog.com/en/1.1.0/)).

## Develop

From this folder:

```bash
python3 -B -m pytest tests -p no:cacheprovider
claude plugin validate . --strict
```

Bump `version` in `.claude-plugin/plugin.json` for each release: installed copies update only when it
changes.

## License

MIT, see [LICENSE](LICENSE).
