"""What the plugin publishes: manifests, the agent files, links, language."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = ROOT.parent.parent
REPOSITORY_ADDRESS = "IlyaTroshchynskyi/ai-skills-registry"
SKILL_DIR = ROOT / "skills" / "decision-debate"
AGENTS_DIR = ROOT / "agents"
ROLES = ("researcher", "architect", "critic", "verifier")
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
# A copy of the regex in plugins/harness-audit/tests/test_package.py: change both together.
PRIVATE = re.compile(r"nix-sdlc|harness_development|troshchynskyi|PycharmProjects|IntervAI|crewai-university"
                     r"|docs/superpowers/plans|calibration\.md|gmail\.com"
                     r"|ai_assistant_langchain|langchain-assistant|aiobotocore|table-split|relational-schema"
                     r"|T06\.3|\bM06\b|evals\.md|dynamodb-over", re.IGNORECASE)
SHIPPED_SUFFIXES = {".md", ".json"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def flat(path: Path) -> str:
    return " ".join(read(path).split())


def manifest(folder: str) -> dict:
    return json.loads(read(ROOT / folder / "plugin.json"))


def split_frontmatter(path: Path) -> tuple[str, str]:
    _, front, body = read(path).split("---\n", 2)
    return front, body


def shipped_files() -> list[Path]:
    skipped = {"tests", ".git", "__pycache__", ".pytest_cache"}
    return [path for path in ROOT.rglob("*")
            if path.is_file() and path.suffix in SHIPPED_SUFFIXES and not skipped & set(path.relative_to(ROOT).parts)]


def test_marketplace_lists_the_plugin_folder() -> None:
    market = json.loads(read(REPOSITORY / ".claude-plugin" / "marketplace.json"))
    assert ("decision-debate", "./plugins/decision-debate") in [(p["name"], p["source"]) for p in market["plugins"]]
    assert not (ROOT / ".claude-plugin" / "marketplace.json").exists()
    entry = next(p for p in market["plugins"] if p["name"] == "decision-debate")
    assert entry["description"] == manifest(".claude-plugin")["description"]


def test_manifest_names_the_plugin_and_its_version() -> None:
    claude = manifest(".claude-plugin")
    assert claude["name"] == "decision-debate"
    assert re.fullmatch(r"\d+\.\d+\.\d+", claude["version"])


def test_plugin_is_for_claude_code_only() -> None:
    assert not (ROOT / ".codex-plugin").exists()
    assert not (SKILL_DIR / "agents").exists()
    assert not (SKILL_DIR / "references" / "roles").exists()
    assert not (ROOT / "scripts").exists()
    assert not (SKILL_DIR / "references" / "cross-model.md").exists()
    assert not [path.name for path in shipped_files()
                if re.search(r"Codex|codex|cross-model|\$decision-debate", read(path))]
    assert "runs in Codex" not in read(REPOSITORY / "README.md")


def test_plugin_is_published_under_mit() -> None:
    assert manifest(".claude-plugin")["license"] == "MIT"
    assert read(ROOT / "LICENSE") == read(REPOSITORY / "LICENSE")
    assert "MIT" in read(ROOT / "README.md").split("## License")[1]


def test_skill_starts_only_when_the_user_asks() -> None:
    front, _ = split_frontmatter(SKILL_DIR / "SKILL.md")
    assert re.search(r"^name: decision-debate$", front, re.MULTILINE)
    assert "disable-model-invocation: true" in front


def test_every_file_the_skill_names_exists() -> None:
    text = read(SKILL_DIR / "SKILL.md")
    paths = set(re.findall(r"`(references/[^`<>]+\.md)`", text))
    assert len(paths) >= 3
    assert not [path for path in sorted(paths) if not (SKILL_DIR / path).is_file()]
    assert all(f"| `decision-debate:decision-{role}` |" in text for role in ROLES)


def test_each_role_is_one_agent_file() -> None:
    assert {path.stem for path in AGENTS_DIR.glob("*.md")} == {f"decision-{role}" for role in ROLES}
    for role in ROLES:
        front, body = split_frontmatter(AGENTS_DIR / f"decision-{role}.md")
        assert re.search(rf"^name: decision-{role}$", front, re.MULTILINE), role
        assert body.lstrip().startswith("# Role: "), role


def test_agents_have_no_file_editing_tools_and_a_known_model() -> None:
    for path in AGENTS_DIR.glob("*.md"):
        front, _ = split_frontmatter(path)
        tools = {tool.strip() for tool in re.search(r"^tools: (.+)$", front, re.MULTILINE).group(1).split(",")}
        assert not tools & {"Edit", "Write", "NotebookEdit", "Agent"}, path.name
        assert re.search(r"^model: (opus|sonnet|haiku|fable|inherit)$", front, re.MULTILINE), path.name


def test_skill_sends_agents_only_the_task_block() -> None:
    text = flat(SKILL_DIR / "SKILL.md")
    assert "Its system prompt already is the role text, so send only the Task block." in text
    assert "general-purpose subagent" not in text


def test_later_rounds_and_devils_advocate_have_inputs_and_an_outcome() -> None:
    text = flat(SKILL_DIR / "SKILL.md")
    assert "Otherwise the mode is `LATER-ROUND`: also pass the open findings and the latest `responses-r*.md`" in text
    assert "If it judges the alternative stronger, record that as a Major finding" in text


def test_agents_stay_out_of_the_workspace_and_verifiers_get_merged_findings() -> None:
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "not to read or search the workspace (`docs/solutions/NNNN-<slug>/`) beyond the files it lists" in skill
    assert "into `findings-rN.md`, without the critic each came from" in skill
    assert "never the `critique-*` files" in skill
    assert "findings-r1.md" in read(SKILL_DIR / "SKILL.md")


def test_finding_ids_are_unique_and_do_not_show_the_source() -> None:
    assert "continue its numbering for the devil's-advocate finding" in flat(SKILL_DIR / "SKILL.md")


def test_orchestrator_and_architect_close_a_rebuttal_by_the_same_rule() -> None:
    rule = "existing evidence by ID that the verifier did not weigh"
    assert rule in flat(SKILL_DIR / "SKILL.md") and rule in flat(AGENTS_DIR / "decision-architect.md")
    assert "A REBUT without new evidence" not in flat(SKILL_DIR / "SKILL.md")


def test_architect_gets_the_brief_and_research_in_every_lead_task() -> None:
    assert flat(AGENTS_DIR / "decision-architect.md").count("Inputs: the brief, the research summary and lens files") == 3
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "rebuttal task, with the brief, `research/summary.md` (plus lens file paths)" in skill
    assert "detail task, for that option, with the brief, the research files" in skill


def test_devils_advocate_has_a_verdict_and_reaches_the_user() -> None:
    assert "`ALTERNATIVE STRONGER` or `PROPOSAL HOLDS`" in flat(AGENTS_DIR / "decision-critic.md")
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "show it to the user in Step 8 as the strongest counter-argument" in skill
    assert "| Except in `lite`, run the devil's-advocate pass if the blast radius is high |" in skill


def test_critic_sees_the_responses_only_in_later_rounds() -> None:
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "Never give it the architect's sketches, drafts, reasoning" not in skill
    assert "Critics see only frozen proposals and, in later rounds, the responses to open findings." in skill
    critic = flat(AGENTS_DIR / "decision-critic.md")
    assert "the architect's" not in critic
    assert "In `LATER-ROUND` you also get the responses to the open findings" in critic


def test_verifier_severity_and_open_questions_reach_the_outcome() -> None:
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "When the verifier lowers or raises a severity, record the new one" in skill
    assert "the proposal's open questions for the user" in skill
    assert "the proposal's open questions for the user" in flat(SKILL_DIR / "references" / "templates" / "report.md")


def test_steps_with_nothing_to_do_are_skipped() -> None:
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "If no critic returned a Critical or Major finding, skip Steps 5 and 6 and go to Step 7." in skill
    assert "If the verifier confirmed no finding, skip this step and go to Step 7." in skill


def test_resume_is_offered_before_a_new_run_starts() -> None:
    skill = flat(SKILL_DIR / "SKILL.md")
    assert skill.index("offer to resume from the last completed step") < skill.index("Otherwise take the next number")
    assert "First check for a run to resume (Workspace, item 2)." in skill
    assert "use that folder as the repository root: first check it for a run to resume (Workspace, item 2)" in skill


def test_brief_asks_about_forks_with_defaults() -> None:
    brief = read(SKILL_DIR / "references" / "templates" / "brief.md")
    assert "## Forks\n" in brief and "## Clarifications\n" in brief
    assert "| Question | Default (assumed if unanswered) | If the other answer | Answer |" in brief
    assert "Fill every checklist row" in flat(SKILL_DIR / "references" / "templates" / "brief.md")
    for area in ("Authentication", "Runtime", "Surroundings", "Access", "Must-haves", "Numbers"):
        assert f"\n| {area}: " in brief, area
    assert "## Asking the user\n" in read(SKILL_DIR / "SKILL.md")
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "the default: what you will assume if they do not answer;" in skill
    assert "Never invent a number that a driver or scenario rests on" in skill
    assert "Do not interrogate the user" not in skill
    assert "Ask at most three questions" not in skill


def test_research_runs_in_two_waves_and_reports_forks() -> None:
    step2 = section(SKILL_DIR / "SKILL.md", "### Step 2.", "### Step 3.")
    assert "**First wave: `codebase`**" in step2 and "**Second wave: every other lens, in parallel**" in step2
    assert "## Forks\n" in read(AGENTS_DIR / "decision-researcher.md")
    assert "Do not split your budget across both branches." in flat(AGENTS_DIR / "decision-researcher.md")


def test_forks_that_flip_the_recommendation_are_asked_before_critique() -> None:
    architect = flat(AGENTS_DIR / "decision-architect.md")
    assert "`flips the recommendation: yes → <option>`" in architect
    assert "Each gives the default, the answer the proposal assumes" in architect
    assert "a short question with options and the default the proposal assumes" in architect
    step3 = section(SKILL_DIR / "SKILL.md", "### Step 3.", "### Step 4.")
    assert "**Forks before critique.**" in step3
    assert "proposal task, with the current proposal added to its inputs; review that version instead" in step3
    assert "detail task" not in step3
    step6 = section(SKILL_DIR / "SKILL.md", "### Step 6.", "### Step 7.")
    assert "An ESCALATE whose answer would change the recommended option goes to the user now" in step6


def test_every_kind_of_answer_has_a_rule_and_every_question_a_time() -> None:
    step6 = section(SKILL_DIR / "SKILL.md", "### Step 6.", "### Step 7.")
    assert "A PARTIAL is checked as both" in step6
    step5 = section(SKILL_DIR / "SKILL.md", "### Step 5.", "### Step 6.")
    assert "user in Step 8, first among the open findings; do not ask about it earlier." in step5
    assert "an unverifiable one raised to Critical goes to the user in Step 8." in step5


def test_a_changed_recommendation_gets_a_full_review() -> None:
    step4 = section(SKILL_DIR / "SKILL.md", "### Step 4.", "### Step 5.")
    assert "The mode is `REVIEW` in round 1 and whenever the recommended option changed since the last review" in step4


def test_agents_never_see_who_wrote_what() -> None:
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "Agents get `settled.md` instead" in skill
    assert "paste into its Task block only the findings it checks" in skill
    assert "| brief, research, settled items |" in skill
    assert "and the progress file" not in section(SKILL_DIR / "SKILL.md", "### Step 4.", "## Writing the report")
    for role in ("architect", "critic"):
        assert "the progress file" not in flat(AGENTS_DIR / f"decision-{role}.md"), role
    assert "Never give this file to an agent" in read(SKILL_DIR / "references" / "templates" / "progress.md")


def test_agents_stay_out_of_the_workspaces() -> None:
    for role in ROLES:
        text = flat(AGENTS_DIR / f"decision-{role}.md")
        assert "Stay out of the workspaces." in text, role
        assert '`glob: "!docs/solutions/*/**"`' in text, role


def test_a_late_answer_sends_the_run_back_not_to_the_start() -> None:
    assert "## Going back instead of starting over\n" in read(SKILL_DIR / "SKILL.md")
    assert "Never start a new run for the same task and never delete working files." in flat(SKILL_DIR / "SKILL.md")
    assert "superseded" in read(SKILL_DIR / "references" / "templates" / "progress.md")


def test_unattended_runs_ask_only_about_the_brief() -> None:
    front, _ = split_frontmatter(SKILL_DIR / "SKILL.md")
    assert "[--unattended]" in front
    assert "- `--unattended`:" in read(SKILL_DIR / "SKILL.md")
    assert "**Assumed without asking:**" in read(SKILL_DIR / "references" / "templates" / "report.md")
    assert "| `--unattended` |" in read(ROOT / "README.md")
    step8 = section(SKILL_DIR / "SKILL.md", "### Step 8.", "## Writing the report")
    assert "With `--unattended`, do not ask: write the report now with the status `proposed`" in step8
    assert "Status: proposed |" in read(SKILL_DIR / "references" / "templates" / "report.md")


def test_agents_are_only_for_the_skill() -> None:
    for role in ROLES:
        front, _ = split_frontmatter(AGENTS_DIR / f"decision-{role}.md")
        assert "Only for the decision-debate skill" in front, role
        assert "Used by the decision-debate skill" not in front, role


def test_wrong_claims_stay_gone() -> None:
    texts = {path.name: flat(path) for path in (ROOT / "README.md", SKILL_DIR / "SKILL.md",
                                               AGENTS_DIR / "decision-verifier.md")}
    assert "cannot edit files" not in texts["README.md"]
    assert "about half" not in texts["decision-verifier.md"]
    assert "only produces real dissent when the role is" not in texts["SKILL.md"]


def test_plugin_does_not_depend_on_other_plugins_or_adrs() -> None:
    texts = {path.name: flat(path).lower() for path in (ROOT / "README.md", SKILL_DIR / "SKILL.md")}
    assert not [name for name, text in texts.items() if "superpowers" in text or "brainstorm" in text]
    assert not re.search(r"\badr\b", texts["SKILL.md"])
    assert not (SKILL_DIR / "references" / "templates" / "adr.md").exists()


def test_any_task_gets_the_analysis_however_short_or_simple() -> None:
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "If it is short, do not ask the user to expand it: fill the gaps from the repository" in skill
    assert "A task that looks simple can hide its risk in the details" in skill
    assert "A task that looks simple usually hides its risk" not in skill
    assert "pays off when the task is large and a wrong decision is expensive" in skill
    assert "single critic pass" not in skill
    assert "## Assumptions" in read(SKILL_DIR / "references" / "templates" / "brief.md")


def test_report_lives_in_docs_solutions_with_its_working_files() -> None:
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "Reports live in `docs/solutions/`" in skill
    assert "Working files go in `docs/solutions/NNNN-<slug>/`, the report in `docs/solutions/NNNN-<slug>.md`" in skill
    assert "`references/templates/report.md`" in skill


def test_architect_offers_two_or_three_options_and_details_the_chosen_one() -> None:
    architect = flat(AGENTS_DIR / "decision-architect.md")
    assert "2–3 genuinely different options that would each solve the task" in architect
    assert "Include doing nothing only when the brief questions whether to do the task at all" in architect
    assert "## Mode `LEAD`, detail task" in read(AGENTS_DIR / "decision-architect.md")
    assert "If they choose an option that is not worked out in full detail yet" in flat(SKILL_DIR / "SKILL.md")


def test_architect_estimates_effort_for_agent_written_code() -> None:
    architect = flat(AGENTS_DIR / "decision-architect.md")
    assert "**Estimate effort with a basis.** Assume the code is written with AI coding agents" in architect
    assert "Compare options by relative size (S, M, L) and name what dominates each." in architect
    assert "list optional hardening separately instead of adding it to the total" in architect
    assert "Effort per the effort rule: S, M or L and what dominates it; days only with their basis." in architect


def test_ready_made_solutions_are_used_or_rejected_never_dropped() -> None:
    researcher = flat(AGENTS_DIR / "decision-researcher.md")
    assert "Ready-made solutions first: managed services of the platform the project already runs on" in researcher
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "the ready-made solutions the dossiers found" in skill
    assert "Check that every ready-made solution in `research/summary.md` is used or rejected" in skill
    architect = flat(AGENTS_DIR / "decision-architect.md")
    assert "**Ready-made before custom.**" in architect
    assert "Every ready-made solution in the research summary appears in the proposal" in architect
    assert "a managed service of the platform or a ready-made tool from the research" in flat(AGENTS_DIR / "decision-critic.md")


def detail_facets() -> list[str]:
    design = read(AGENTS_DIR / "decision-architect.md").split("## Detailed design\n")[1].split("\n## ")[0]
    return [line[4:] for line in design.splitlines() if line.startswith("### ")]


def test_facets_are_a_checklist_for_the_architect() -> None:
    facets = detail_facets()
    assert len(facets) >= 12 and "Validation, errors and edge cases" in facets and "Implementation steps" in facets
    assert "The facets are a checklist so that nothing is missed" in flat(AGENTS_DIR / "decision-architect.md")
    assert "Not applicable: <reason>" in read(AGENTS_DIR / "decision-architect.md")
    assert "**Every facet answered.**" in read(SKILL_DIR / "SKILL.md")


def test_report_is_short_and_puts_the_answer_first() -> None:
    template = read(SKILL_DIR / "references" / "templates" / "report.md")
    headings = re.findall(r"^## (.+)$", template, re.MULTILINE)
    assert headings[:4] == ["In short", "Decision", "Options", "Easy to miss"]
    assert {"How it works", "Key decisions", "Risks and open issues", "Plan", "More detail"} <= set(headings)
    assert not {"Solution in detail", "Debate record", "Sub-decisions"} & set(headings)
    assert "proposal-vN.md" in template
    rules = section(SKILL_DIR / "SKILL.md", "## Writing the report\n", "\n## Rules you enforce")
    for phrase in ("Keep the report under about 1200 words.", "Translate everything, headings included.",
                   "**No evidence or finding IDs**", "Name only files and modules that exist in the repository.",
                   "**Traps get the space.**"):
        assert phrase in rules, phrase
    assert "following Writing the report below" in flat(SKILL_DIR / "SKILL.md")
    assert "under about 1200 words" in flat(ROOT / "README.md")


def test_design_stays_at_decision_level() -> None:
    architect = flat(AGENTS_DIR / "decision-architect.md")
    assert "**Decision level, not implementation level.**" in architect
    assert "not DDL or column lists" in architect and "not every field and error code" in architect
    assert "about 800 words in all" in architect
    assert "enough detail that someone could implement it without guessing" not in architect
    assert "a missing schema, field list or error-code list is not a finding" in flat(AGENTS_DIR / "decision-critic.md")
    assert "| The proposal spells out schemas, field lists, error catalogs" in read(SKILL_DIR / "SKILL.md")


def test_critic_audits_the_detail_and_researchers_cover_ux() -> None:
    assert "**Detail audit.**" in read(AGENTS_DIR / "decision-critic.md")
    assert "### `ux`" in read(AGENTS_DIR / "decision-researcher.md")


def test_it_pays_off_on_large_costly_tasks_not_on_simple_ones() -> None:
    front, _ = split_frontmatter(SKILL_DIR / "SKILL.md")
    assert "For a large task where a wrong decision is expensive to undo." in " ".join(front.split())
    assert "including ones that look simple" not in front
    readme = flat(ROOT / "README.md")
    assert "It pays off most on tasks that look simple" not in readme
    assert "Use it when a task is large and a wrong decision would be expensive to undo" in readme
    assert "For a small change that is easy to undo it is too expensive." in readme


def test_readme_cites_the_design_basis() -> None:
    basis = read(ROOT / "README.md").split("## Why it works this way")[1].split("\n## ")[0]
    assert len(re.findall(r"\]\(https://", basis)) >= 7


def test_readmes_explain_install_from_this_repository() -> None:
    for readme in (ROOT / "README.md", REPOSITORY / "README.md"):
        text = read(readme)
        assert f"claude plugin marketplace add {REPOSITORY_ADDRESS}" in text, readme
        assert "decision-debate@troshchynskyi-plugins" in text and "/decision-debate:decision-debate" in text, readme


def test_person_gets_messages_and_the_report_in_their_language() -> None:
    assert "Write messages to the user and the report in the language the user invoked you in." in flat(SKILL_DIR / "SKILL.md")


def test_shipped_text_is_in_english() -> None:
    leftovers = [f"{path.relative_to(ROOT)}:{number}" for path in shipped_files()
                 for number, line in enumerate(read(path).splitlines(), 1) if CYRILLIC.search(line)]
    assert not leftovers, leftovers


def test_nothing_private_is_published() -> None:
    leaks = [f"{path.relative_to(ROOT)}:{number}" for path in shipped_files()
             for number, line in enumerate(read(path).splitlines(), 1)
             if PRIVATE.search(line.replace(REPOSITORY_ADDRESS, ""))
             and "Illia Troshchynskyi" not in line and "troshchynskyi-plugins" not in line]
    assert not leaks, leaks


def test_skill_never_searches_the_machine_for_the_project() -> None:
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "Never look for the project yourself: do not list, search or read folders outside the current working directory" in skill
    assert "stop and ask the user one question before anything else: where the project is, or whether to continue without project context" in skill
    assert "Without project context, treat the task as new" in skill and "drop the `codebase` lens" in skill
    assert "the repository root if there is one (agents read nothing outside it)" in skill
    assert "| The folder has no code for the task | Ask where the project is" in read(SKILL_DIR / "SKILL.md")
    assert "**Stay inside the repository root**" in read(AGENTS_DIR / "decision-researcher.md")
    assert "- Report: docs/solutions/NNNN-<slug>.md" in read(SKILL_DIR / "references" / "templates" / "brief.md")
    assert "it never searches your computer for it" in flat(ROOT / "README.md")
    assert "If the repository has no code for this task" not in skill


def section(path: Path, start: str, end: str) -> str:
    return " ".join(read(path).split(start)[1].split(end)[0].split())


def runs_besides_researchers(path: Path) -> list[str]:
    row = next(line for line in read(path).splitlines() if line.startswith("| Agent runs besides researchers |"))
    return re.findall(r"about \d+–\d+", row)


def test_profiles_set_the_cost() -> None:
    skill = read(SKILL_DIR / "SKILL.md")
    front, _ = split_frontmatter(SKILL_DIR / "SKILL.md")
    assert "[--profile lite|standard|deep]" in front
    assert "- `--profile lite|standard|deep`: how much to spend (see Profiles)." in skill
    assert "overrides the profile's default, maximum 3" in skill
    assert "## Profiles\n" in skill and "| | `lite` | `standard` | `deep` |" in skill
    assert "Put the researcher budget into every researcher's Task block." in skill
    assert runs_besides_researchers(SKILL_DIR / "SKILL.md") == runs_besides_researchers(ROOT / "README.md") == [
        "about 2–4", "about 3–9", "about 10–19"]


def test_lenses_follow_the_task_and_the_profile_only_sets_depth() -> None:
    skill_text = read(SKILL_DIR / "SKILL.md")
    skill = flat(SKILL_DIR / "SKILL.md")
    readme_text = read(ROOT / "README.md")
    readme = flat(ROOT / "README.md")
    assert "| Lenses |" not in skill_text and "| Typical agent runs |" not in skill_text
    assert "| Typical agent runs |" not in readme_text
    assert "The profile does not limit the lenses." in skill
    assert "overrides your own choice of lenses" in skill
    assert "one run per lens plus the profile's own runs" in skill
    assert "`prior-art`: for every task" in skill
    assert "including the profile and the lenses" in skill
    assert "The profile sets how many lenses run." not in skill
    assert "overrides the profile's default. `security-data`" not in skill
    assert "run the most relevant other lens in its place" not in skill
    assert "| `--lenses a,b,c` | chosen from the task in the brief |" in readme
    assert "one researcher per lens plus this row" in readme
    assert "per profile (+ security-data when relevant)" not in readme


def test_progress_file_starts_with_the_brief_and_follows_every_step() -> None:
    step1 = section(SKILL_DIR / "SKILL.md", "### Step 1.", "### Step 2.")
    assert "Save `brief.md` once approved and create `progress.md` from `references/templates/progress.md`." in step1
    assert "Add the recommended profile and its estimated number of agent runs." in step1
    assert "Create `progress.md`" not in section(SKILL_DIR / "SKILL.md", "### Step 3.", "### Step 4.")
    assert "Update the progress file after **every** completed step" in read(SKILL_DIR / "SKILL.md")
    assert "Do not re-read files you have already summarised" in flat(SKILL_DIR / "SKILL.md")
    assert read(SKILL_DIR / "references" / "templates" / "progress.md").startswith("# Progress: NNNN")
    assert not [path.name for path in shipped_files() if "ledger" in read(path).lower()]


def test_cheaper_profiles_skip_sketches_devils_advocate_and_batch_verification() -> None:
    skill = flat(SKILL_DIR / "SKILL.md")
    assert "**Option sketches (`deep` only).**" in skill
    assert "Except in `lite`: if round 1 returns zero Critical or Major findings" in skill
    assert "In `lite` and `standard`, spawn **one** verifier with all of them" in skill
    assert "In `deep`, spawn one verifier per finding" in skill
    assert "- **Budget.** Respect the profile, the researcher budgets and the round cap" in skill


def test_roles_carry_their_budgets() -> None:
    researcher = read(AGENTS_DIR / "decision-researcher.md")
    assert "## Budget\n" in researcher and "your budget, the repository root" in flat(AGENTS_DIR / "decision-researcher.md")
    assert "Network access from the shell (`curl`, `gh`, `wget`, package managers) counts against the fetch budget." in flat(
        AGENTS_DIR / "decision-researcher.md")
    assert "Up to 10 bullets" in researcher and "5–10 bullets" not in researcher
    assert not [path.name for path in (SKILL_DIR / "SKILL.md", ROOT / "README.md") if "until saturation" in read(path)]
    assert "≤20 searches, ≤12 fetches, stop earlier at saturation" in read(SKILL_DIR / "SKILL.md")
    assert "**Ceiling, not quota.** Report at most 7 findings in full" in flat(AGENTS_DIR / "decision-critic.md")
    assert "Zero findings is a valid outcome." in flat(AGENTS_DIR / "decision-critic.md")
    verifier = flat(AGENTS_DIR / "decision-verifier.md")
    assert "One or more findings, each with its claim" in verifier
    assert "Repeat the block for every finding you received, in the order given." in verifier
    assert "Keep the proposal under about 1800 words, not counting the detailed design" in flat(AGENTS_DIR / "decision-architect.md")
    assert "- Profile: lite | standard | deep (estimated agent runs: N)" in read(SKILL_DIR / "references" / "templates" / "brief.md")


def test_agent_models_follow_the_cost_plan() -> None:
    models = {path.stem: re.search(r"^model: (\S+)$", split_frontmatter(path)[0], re.MULTILINE).group(1)
              for path in AGENTS_DIR.glob("*.md")}
    assert models == {"decision-researcher": "sonnet", "decision-architect": "opus",
                      "decision-critic": "opus", "decision-verifier": "sonnet"}
    assert "one or more review findings, one at a time" in read(AGENTS_DIR / "decision-verifier.md")


def test_readme_documents_profiles_and_savings() -> None:
    readme = flat(ROOT / "README.md")
    assert "[--profile lite|standard|deep] [--rounds N] [--lenses a,b,c] [--unattended] <task>" in readme
    assert "## Profiles and cost" in read(ROOT / "README.md")
    assert "--profile lite Which queue should carry order events?" in readme
    assert "`/model sonnet`" in readme and "resume from the progress file" in readme
