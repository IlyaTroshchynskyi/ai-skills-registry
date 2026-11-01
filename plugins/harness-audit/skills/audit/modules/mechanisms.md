# Module I. Mechanisms: hooks, permissions, subagents, MCP, plugins

## Contents

- How to choose a mechanism
- Hooks
- Permissions and settings
- Subagents
- MCP
- Plugins

Inputs: `settings`, `mcp` and `agent` files from the inventory (`instruction_inventory.py`), `hooks` in
`.claude/settings*.json` and `~/.claude/settings.json`, formatter and linter configs, `/insights` data.

"Sign → hook / subagent" tables and what is not carried over from them are in
`references/skill-sources.md`.

## How to choose a mechanism

An instruction in `CLAUDE.md` or a skill is a request, not a guarantee. A hook or a permission rule is
enforcement. If a rule must always hold, it belongs in a hook or permissions.

The ladder for a recurring instruction:

1. Corrected twice in chat → a line in `CLAUDE.md`.
2. Applies only to some paths → a rule with `paths`.
3. A multi-step or rare procedure → a skill.
4. Still violated, or a violation is costly, and a program can check it → a hook or permission rule.
   Then remove the prose line: now it only costs context ("What to remove" section).

Add a mechanism only against an observed failure or a clear risk. "Nothing to add" is a valid result.

## Hooks

A hook and its script appear in a recommendation in full: the JSON for `.claude/settings.json` and the
complete script text, not a fragment.

The contract the checks rely on:
- exit 2 — blocks, the reason goes to stderr;
- exit 1 — does not block;
- default timeout — 600 s;
- `Stop` fires at the end of every response, not of a task.

Committed hooks run with the user's rights, outside the sandbox, and in `-p` mode without the trust
dialog. Their scripts deserve the same review as CI scripts.

- **HK-01. A formatter exists but no formatting hook.** There is a Prettier, Biome, Black, Ruff, gofmt
  or rustfmt config but no `PostToolUse` with an `Edit|Write` matcher. → A hook that formats only the
  changed file.
- **HK-02. No back-pressure path.** Typecheck, lint and test commands exist, but there is no edit hook,
  no `Stop` gate and no written verification command. → A `Stop` hook running a fast check (lint,
  typecheck): silent on success, on failure exits with code 2 and prints only the errors. No slow
  commands and no commands that need services.
- **HK-03. A hook points to a missing or non-executable script.** Resolve `command` to a file, check
  the executable bit. A relative path without `$CLAUDE_PROJECT_DIR` is also a finding.
- **HK-06. A `Stop` hook without a `stop_hook_active` check.** Without it the hook can block stopping
  in a loop (after eight blocks in a row Claude Code disables it). → The script reads
  `stop_hook_active` from the input JSON and exits with code 0 when it is `true`.
- **HK-07. A slow or unbounded hook.** A synchronous hook on every tool call without a `timeout` field,
  or with the full test suite, or slow in practice: this project's hook timings are in `/doctor`
  output. Threshold in `references/thresholds.md`. → An explicit short `timeout`, scope limited to the
  changed file; the full test suite does not belong in a hook.

The other hook checks (HK-04, HK-05, HK-08…HK-13) come after calibration.

## Permissions and settings

Shared settings live in `.claude/settings.json` under git. Personal ones live in
`.claude/settings.local.json`, which is ignored.

A Bash deny or ask rule matches command text and is not a security boundary: `Bash(git push *)` does
not stop `git -C . push`.

- **PRM-01. Secrets without a read ban.** `.env*`, `secrets/` and keys exist, but `permissions.deny`
  has no `Read(./.env)`, `Read(./.env.*)`, `Read(./secrets/**)`. Read-deny also covers Edit and Write on
  the same path. → `Read(...)` rules in the shared `.claude/settings.json`. Destructive commands
  (`git push --force`, `rm -rf`) → an `ask` rule plus a `PreToolUse` hook; for OS-level isolation, the
  sandbox.
- **PRM-02. A ban that does not work.** Path rules on `Write(...)`, `Glob(...)`, `MultiEdit(...)` are
  accepted but not applied: file permissions read only `Edit(path)` and `Read(path)`. A `.claudeignore`
  file has no effect. → Replace with `Read(...)` / `Edit(...)`.
- **PRM-03. Allow rules that are too broad.** `Bash`, `Bash(*)`, `Bash(git *)`, `Bash(python *)`,
  `Bash(node *)`, `Bash(npx *)`, `Bash(docker exec *)`. → Specific project commands:
  `Bash(npm run test *)`, `Bash(make check)`.
- **PRM-09. No allow rules for the project's own commands.** Lint, test and build commands are written
  in the instructions but have no `allow` rules; `/insights` data shows a high
  `bash_would_prompt_count`. → `Bash(npm run test *)`, `Bash(make check)` and the like in the shared
  `.claude/settings.json`, not auto mode.
- **PRM-07. Personal settings in git.** `settings.local.json` is tracked by git, or a committed `env`
  block contains secrets. → Remove from git, add to `.gitignore`; rotate the secret.

Auto mode is not recommended (the "Never recommend" list in `SKILL.md`). The other permission checks
(PRM-04…PRM-06, PRM-08, PRM-10, PRM-11) come after calibration; PRM-11 is partly covered by E5 in
`checklist.md`.

## Subagents

A subagent is recommended only for a structural reason, at least one of four:

- isolating bulky output that the main conversation does not need;
- parallel independent work;
- a fresh unbiased context, such as reviewing code it did not write;
- a hard boundary of tools and permissions, such as read-only.

A job title ("frontend engineer", "test-writer") gives no such reason: job-title agents are not
recommended. Subagents are also not needed for small sequential work in one file. Keep the roster
small: many similar descriptions make automatic delegation unreliable.

What is usually justified: a reviewer in a fresh context with read-only tools (connected to D2 in
`checklist.md`), a read-only researcher for bulky searches, an agent with limited permissions for a
risky area.

- **SUB-01. An agent file will be skipped.** No `name` or `description`; frontmatter does not start on
  the first line; YAML does not parse. Check: `claude plugin validate <.claude directory>`.
- **SUB-03. Invalid `model`.** A value other than `sonnet`, `opus`, `haiku`, `fable`, `inherit` or a
  valid full model ID (example: `model: sonet`).

In a recommendation for a new subagent: name, structural reason, `description` with the invocation
condition, the `tools` list, the output contract (what to return, how briefly, with `file:line`). The
other checks (SUB-02, SUB-04…SUB-10) come after calibration.

## MCP

A CLI is the most economical way to work with an external system. MCP is justified when the system has
no good CLI, when authentication or session state is awkward from a shell, or when a browser is needed.
If a CLI is already in use (`gh`, `psql`), do not recommend MCP for the same thing (MCP-03, B4 in
`checklist.md`). Local MCP servers run outside the sandbox with the user's rights; servers that read
external content open a path for prompt injection.

- **MCP-02. Credentials and transport.** Literal tokens in `headers`, `env`, `args` of `.mcp.json`;
  `http://` to a remote host. → `${VAR}` and a way to set it; https.
- **MCP-06. Unpinned launch and DB writes.** `npx -y pkg@latest`, `uvx` without a version; a DB DSN
  without read-only mode. → Pin the version; a read-only DB user, not production.
- **MCP-08. The person needs an MCP server they do not have.** There is no ready "system → server" list:
  candidates are derived from this person's and project's data. The grounds are a proven need or a
  system from the stack that the agent has to work with and nothing covers.
  1. **What is needed.** Where the agent stumbles or what it cannot do: friction and failed commands in
     `/insights`, work the person does for the agent (pasting logs, data, check results), external
     systems and libraries from dependencies and configs that the agent has to work with.
  2. **What already exists.** Connected MCP servers and plugins, CLIs the agent uses without errors
     according to the history, built-in tools. If they cover a need, MCP is not needed (MCP-03). What
     remains are the needs for which the person does not use anything yet.
  3. **Where to search.** For each remaining need, `scripts/find_skill_candidates.py` over the
     `claude plugin list --json --available` catalog (recipe in `references/skill-sources.md`); with
     consent to network, also at the vendor of that system or library, only its GitHub and
     documentation. A `popular` tier candidate goes in the "Worth a look" format.

  → A recommendation in the "Install" format from `modules/skills.md`: source tier, "What changes for
  you", cost, the 9-item security check, MCP-06 (pinned version; for a DB, read-only and not
  production), the connect command. Location: `.mcp.json` is "in repo", user scope is "personal". If
  what already exists covers the need, one line in "Checked and fine": "<need> — covered by <what>".

The others (MCP-01, MCP-04, MCP-05, MCP-07) come after calibration.

## Plugins

A plugin is a packaging layer for several repositories. An enabled plugin takes part in every session.
Permission rules, `CLAUDE.md` and rules do not move into a plugin.

- **PLG-01. A plugin is enabled but its marketplace is not declared.** `enabledPlugins` in
  `.claude/settings.json` without a matching `extraKnownMarketplaces`, or a `directory` source with an
  absolute local path. A colleague will not be able to install it. → Declare the marketplace in the
  project settings.

The others (PLG-02…PLG-05) come after calibration; unused plugins are F2 in `checklist.md`.
