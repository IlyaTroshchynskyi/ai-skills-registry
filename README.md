# ai-skills-registry

Claude Code plugins by Illia Troshchynskyi.

## Install

```bash
claude plugin marketplace add IlyaTroshchynskyi/ai-skills-registry
claude plugin install harness-audit@troshchynskyi-plugins
claude plugin install decision-debate@troshchynskyi-plugins
```

Install only the plugins you need.

## Plugins

| Plugin | Command | What it does |
| --- | --- | --- |
| [harness-audit](plugins/harness-audit) | `/harness-audit:audit` | Audits a repository and your Claude Code setup, then writes a report with evidence-backed recommendations |
| [decision-debate](plugins/decision-debate) | `/decision-debate:decision-debate` | Works out a solution for a task from several angles: 2–3 options, an architect and an independent critic debate them, and a short report you choose from |

## Rules

Plugins cannot ship rules, so copy a rule into the project that needs it, from a clone of this
repository:

```bash
mkdir -p .claude/rules
cp <clone>/rules/naming.md <clone>/rules/naming-python.md .claude/rules/
```

| Rule | Loads for | What it sets |
| --- | --- | --- |
| `comments.md` | Every file | No comments in code, with one exception |
| `naming.md` | Every file | Naming in any language |
| `naming-python.md` | `**/*.py` | How Python spells those names |
| `naming-js.md` | `**/*.{js,jsx,ts,tsx}` | How JavaScript and TypeScript spell those names |

The language files add to `naming.md`, so copy it with them. A copy does not update by itself: copy it
again after a change here. Do not symlink: a rule with `paths` does not load through a link that points
outside the project.

## Add to the registry

- **Plugin:** put it in `plugins/<name>/` and list it in `.claude-plugin/marketplace.json`. Each plugin
  folder carries its own license files: an install copies only that folder.
- **Rule:** put it in `rules/` and add it to the table above.

## License

MIT, see [LICENSE](LICENSE). A plugin may include material under other licenses: see the notices in its
folder.
