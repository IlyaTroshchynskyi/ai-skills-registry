# Thresholds

Thresholds are configurable: the values below are defaults from the research. None has been validated
on a sample of repositories; during calibration a value may change, and the source stays in the table.
A value near a threshold is not a finding but a reason to look at the content.

| ID | Threshold | Source |
| --- | --- | --- |
| CTX-S1 | Root `CLAUDE.md` / `.claude/CLAUDE.md` / `AGENTS.md`: more than 200 lines is a finding. Same threshold for nested `CLAUDE.md` (A2) | Anthropic: "target under 200 lines" — [Memory](https://code.claude.com/docs/en/memory); unrot: >100 lines warn, >200 error — [unrot](https://github.com/unrot-dev/unrot) |
| CTX-S2 | Any instruction file over 40,000 characters or `startup_chars` over 40,000 is a finding. Claude Code publishes no overall limit | Claude Code warning at about 40,000 characters, as `/doctor` described it during calibration (2026-10-17); [Memory](https://code.claude.com/docs/en/memory) |
| SK-03 | `description` over 1,024 characters (portability) or `description` + `when_to_use` over 1,536 is a finding | [Skills frontmatter](https://code.claude.com/docs/en/skills#frontmatter-reference); [agentskills.io](https://agentskills.io/specification) |
| SK-10 | `SKILL.md` body over 500 lines is a finding; over ~5,000 tokens is a remark | [Skill authoring](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices); sources disagree on the numbers |
| FB-03 | Edit hook: seconds; pre-commit under ~5 s; default test under 120 s or a fast subset exists; "verify everything" under 10 min | Claude Code Bash timeouts: 2 min by default and 10 min at most, [Tools reference](https://code.claude.com/docs/en/tools-reference); the other numbers are a synthesis of the research |
| FB-04 | On success, no more than ~20 lines of output; on failure, no more than ~10,000 characters or output to a file | Long output of a failed command is truncated: [Tools reference](https://code.claude.com/docs/en/tools-reference); 20 lines is a synthesis of the research |
| HK-07 | A synchronous hook on every tool call: an explicit `timeout` (default 600 s); a normal run under 2 s | [Hooks reference](https://code.claude.com/docs/en/hooks); the 2 s threshold is how `/doctor` applied it during calibration |
| H3 | A third-party repository in "Worth a look": at least 3,000 stars, last change no older than 180 days, not archived | Project decision of 2026-10-31, compared on 9 repositories during calibration |
| G10 | The structure diagram has no more than ~25 nodes; past that, one node for a group of files | Project decision of 2026-11-07 |
| CMD-17 | "Verify everything" covers all blocking CI jobs, is silent on success, takes under 10 min | [GitHub Docs](https://docs.github.com/en/copilot/tutorials/coding-agent/get-the-best-results); time as in FB-03 |
