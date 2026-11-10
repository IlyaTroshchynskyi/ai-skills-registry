# harness-audit

A Claude Code plugin that audits a repository and your personal Claude Code setup, then writes a report
with evidence-backed recommendations: instructions, verification commands, documentation, skills,
rules, hooks, subagents and MCP.

The audit works for any project, including one you did not write. Its main goal is relevance: every
recommendation rests on a file, a command output or your own session history, and comes with a
ready-made change.

## Install

```bash
claude plugin marketplace add IlyaTroshchynskyi/ai-skills-registry
claude plugin install harness-audit@troshchynskyi-plugins
```

Requires Python 3.10 or later and git.

## Use

Start Claude Code in the root of the project and run:

```text
/harness-audit:audit
```

With no arguments it checks every area, which is expensive. Start with a few:

```text
/harness-audit:audit instructions skills mechanisms
```

| Area | What it checks |
| --- | --- |
| `instructions` | `CLAUDE.md`, `AGENTS.md`, rules: size, links, facts, contradictions |
| `spec` | Whether the agent can find specs and verify acceptance criteria |
| `verification` | One command to verify everything, tests, CI parity |
| `review` | Whether review is independent and part of the Definition of Done |
| `environment` | Reproducibility, secrets, parallel work |
| `hygiene` | Clutter and unused harness |
| `docs` | Documentation structure, duplicates, staleness, ADRs, glossary, PR template |
| `skills` | Which skills to improve, create, install or disable |
| `mechanisms` | Hooks, permissions, subagents, MCP, plugins |
| `history` | Built-in diagnostics and your session history |
| `design` | How you discuss decisions with the agent before code |

## What it does and does not touch

- It only reads. The one file it writes is the report, `harness-audit-<date>.md`, in the repository
  root. It never edits your harness, installs packages or commits.
- It asks first, in one message, before anything expensive, personal or executable: reading session
  data, running project commands, using the network.
- With consent to network, only general search words and names of public repositories leave your
  machine. They go to skills.sh and the GitHub API.
- The report contains data about your personal setup and sessions. Review the items labeled "personal"
  before sharing it. Do not commit it.

The skill speaks and writes the report in the language of your conversation.

## Develop

From this folder:

```bash
python3 -B -m pytest tests -p no:cacheprovider
claude plugin validate . --strict
claude plugin validate ../.. --strict
```

The second validation checks the marketplace in the repository root.

Bump `version` in `.claude-plugin/plugin.json` for each release: installed copies update only when it
changes.

## License

MIT, see [LICENSE](LICENSE). The tables adapted from `claude-automation-recommender` remain under the
Apache License 2.0, see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
