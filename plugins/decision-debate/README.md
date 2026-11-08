# decision-debate

A Claude Code plugin that works out a solution for a development task **before you write code**, from
several angles. It researches the task, has an architect propose 2–3 options and work out
the best one in detail while an independent critic attacks it, checks every serious finding against the
code, and ends with a short report you can read in a few minutes: the recommendation and what it costs,
the options, what is easy to miss and how the solution works. You choose. It never starts on its own.

## Install

```bash
claude plugin marketplace add IlyaTroshchynskyi/ai-skills-registry
claude plugin install decision-debate@troshchynskyi-plugins
```

## Invoke

```text
/decision-debate:decision-debate [--profile lite|standard|deep] [--rounds N] [--lenses a,b,c] [--unattended] <task>
```

Examples:

```text
/decision-debate:decision-debate --profile lite Which queue should carry order events?
/decision-debate:decision-debate --profile standard Monolith module or separate billing service?
/decision-debate:decision-debate --profile lite --lenses codebase,prior-art,operations Replace our ORM?
```

Without `--profile`, the skill recommends one in the brief, with an estimated number of agent runs, and
you confirm or change it there before any research starts.

Describe the task in as much or as little detail as you have. With a short description the skill reads
the repository, writes down its assumptions, and asks you to correct them.

| Argument | Default | Meaning |
| --- | --- | --- |
| task | required | the task or question, in plain words |
| `--profile` | recommended in the brief | `lite`, `standard` or `deep`: how much to spend (see Profiles and cost) |
| `--rounds N` | per profile | critique and rebuttal rounds, maximum 3 |
| `--lenses a,b,c` | chosen from the task in the brief | research lenses: codebase, requirements, ux, prior-art, operations, security-data |
| `--unattended` | off | ask only about the brief; later open points take their defaults and the report lists them |

If the task's code is not in the folder you started in, the skill first asks where the project is, or
whether to work without project context; it never searches your computer for it.

Then it asks you only where your answer could change the direction. In the brief you approve its
assumptions, the profile and the lenses and answer its forks: quick questions such as how users
authenticate or where the service runs, each with the answer the skill will assume if you skip it.
Answer "go on" to accept them all. More forks may come after the code is read, after the research, before the critique when the
recommendation depends on your answer, and when a reviewer's point needs your call; a checkpoint with
nothing to ask is skipped. At the end you choose an option. If an answer contradicts work already done,
the skill redoes only the affected part instead of starting over. With `--unattended` you are asked only
about the brief, and the report ends with the questions that pick the option instead of your choice.

## Profiles and cost

| | `lite` | `standard` | `deep` |
| --- | --- | --- | --- |
| Searches per researcher | ≤6 | ≤10 | ≤20 |
| Options | lead architect only | lead architect only | 2–3 parallel sketches, then lead |
| Rounds | 1 | up to 2 | up to 3 |
| Verification | one verifier for all serious findings | one verifier per round | one verifier per finding |
| Agent runs besides researchers | about 2–4 | about 3–9 | about 10–19 |

The profile sets depth: how much each researcher may search, how many rounds, how much is verified. It
does not limit the lenses (the angles, one researcher each). The skill picks them from your task and
lists each in the brief with the reason; you add or drop any there, or pass `--lenses`. The total is one
researcher per lens plus this row: four lenses on `standard` come to about 7–13 runs. The brief gives
the figure for your task.

More ways to save:

- Run the orchestrator on a cheaper model (`/model sonnet`); subagents keep their own models.
- Drop a lens in the brief that your task does not need: each one is a researcher with its own search
  budget.
- Narrow the decision before invoking.
- If limits run out mid-run, invoke again with the same question and accept the offer to resume from the
  progress file.

## When to use it

Use it when a task is large and a wrong decision would be expensive to undo: a new feature, a change to
how data is stored, an integration, a public API, a major dependency. The larger the task and the higher
the cost of a mistake, the more it pays off, because a flaw found in the design costs far less than one
found after delivery (see the sources below). The analysis goes into the details where mistakes tend to
hide: input validation, permissions, storage, caching and what the user sees when something fails.

For a small change that is easy to undo it is too expensive.

## Output

`docs/solutions/NNNN-<slug>.md`, the report, under about 1200 words and in your language:

- in short: the recommendation, why, what it costs and what is not ready yet;
- the decision, or the 1–3 questions whose answers pick the option;
- 2–3 options side by side;
- what is easy to miss, and what the solution does about each point;
- how the chosen solution works, in a few steps, and its key decisions;
- risks and open issues, a plan in milestones, and what would make another option better later.

The report stays at decision level: where data lives rather than the schema, endpoints rather than every
field and error code. The full design is in the final proposal, and the detailed plan by file is best
made after you choose, against the code.

The working files sit next to it in `docs/solutions/NNNN-<slug>/`: brief, research dossiers, option
sketches, proposals, critiques, merged findings, verifications, the progress file and `settled.md`, the
part of the record the agents see. Commit them or not,
as you prefer.
If you pick an option other than the recommended one, the skill works it out in the same detail and
reviews it once more before writing the report.

## Layout

```
.claude-plugin/plugin.json      manifest
skills/decision-debate/         the skill: SKILL.md and templates
  references/templates/         brief, progress file and report
agents/                         the four roles as subagents: each file is the role prompt
tests/                          checks of the manifest, agents and links
```

## Agents

The skill runs four named subagents (`decision-debate:decision-researcher`, `-architect`, `-critic`,
`-verifier`). They have no Edit or Write tool. They keep Bash for read-only commands such as `git log`,
and those commands still go through your permission settings. Each has its own model:

- architect and critic: `opus`;
- researcher and verifier: `sonnet`.

## Why it works this way

The skill follows what research on multi-agent debate and LLM self-correction shows, rather than "more
agents, more rounds":

- **Independence over conversation.** Majority voting accounts for most of the gains usually credited to
  multi-agent debate ([Choi et al., 2025](https://arxiv.org/abs/2508.17536)), and debate does not
  reliably beat simpler ensembles ([Smit et al., 2024](https://arxiv.org/abs/2311.17371)). In debate,
  agents often switch from correct to incorrect answers under peer influence, and longer debates can do
  worse ([Wynn et al., 2025](https://arxiv.org/abs/2509.05396)). Hence roles work in isolation on frozen
  files, with 1 to 3 rounds depending on the profile.
- **A separate critic with evidence.** Models rarely correct their own reasoning without outside feedback
  ([Huang et al., 2024](https://arxiv.org/abs/2310.01798)), and an assigned devil's advocate is weaker
  than authentic dissent ([Nemeth et al., 2001](https://doi.org/10.1002/ejsp.58)). Hence the critic is a
  separate agent, must cite code or sources, and every serious finding goes to an independent verifier.
- **You are the judge.** LLM evaluators recognise and favour their own generations ([Panickssery et al.,
  2024](https://arxiv.org/abs/2404.13076)). Hence no agent decides.
- **Forks asked early.** Finding and fixing a problem after delivery is often 100 times more expensive
  than during requirements and design, and avoidable rework takes 40 to 50 percent of the effort
  ([Boehm and Basili, 2001](https://www.cs.umd.edu/projects/SoftEng/ESEG/papers/82.78.pdf)). Asking
  about ambiguous requirements raised GPT-4's code generation pass rate from 71% to 81% ([Mu et al.,
  2023](https://arxiv.org/abs/2310.10996)), and asking pays off most where the possible intents differ
  ([Zhang and Choi, 2023](https://arxiv.org/abs/2311.09469)). Hence the brief lists forks with defaults,
  each checkpoint asks only when there is a fork, and a late answer sends the run back to the step it
  affects instead of to the start.
- **Cost.** Multi-agent systems use many times the tokens of a single chat ([Anthropic,
  2025](https://www.anthropic.com/engineering/multi-agent-research-system)), so the skill is for tasks
  where a worked-out solution is worth it.
- **Format.** The options and the chosen outcome follow the structure of [MADR
  4.0](https://adr.github.io/madr/); the critic's pre-mortem follows [Klein,
  2007](https://hbr.org/2007/09/performing-a-project-premortem).
- **A short report at decision level.** Readers of a web page read about 20% of its words ([Nielsen,
  2008](https://www.nngroup.com/articles/how-little-do-users-read/)). A decision record should be one or
  two pages long ([Nygard,
  2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)), and a design doc
  should resist copying in formal interface or data definitions, which are verbose and soon out of date
  ([Ubl, 2020](https://www.industrialempathy.com/posts/design-docs-at-google/)). Hence the report puts
  the answer first, stays under about 1200 words and leaves schemas to the implementation plan.

## Editing

Edit a role prompt in `agents/`, bump `version` in `.claude-plugin/plugin.json`, run the tests, and
commit.

```bash
python3 -B -m pytest tests -p no:cacheprovider
claude plugin validate . --strict
```

## Requirements and limits

- Web search must be available to subagents for the `prior-art` research lens.
- The number of agent runs depends on the profile and on the number of lenses: see Profiles and cost.
- Not yet exercised end to end in live sessions. Run it on one real task first and tune the role prompts.

## License

MIT, see [LICENSE](LICENSE).
