from __future__ import annotations

import re
from pathlib import Path

from helpers import load_script

SKILL_DIR = Path(__file__).parent.parent / "skills" / "audit"


def read(rel: str) -> str:
    return (SKILL_DIR / rel).read_text(encoding="utf-8")


def flat(text: str) -> str:
    """Text without line breaks: a phrase can wrap at a line boundary."""
    return " ".join(text.split())


def assert_ids(rel: str, ids: list[str]) -> None:
    text = read(rel)
    missing = [i for i in ids if not re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", text)]
    assert not missing, f"{rel}: missing {missing}"


def test_checklist_keeps_v1_items_and_adds_p1() -> None:
    v1 = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4",
          "C6", "C7", "C8", "C9", "D1", "D2", "D3", "D4", "D5", "D6", "E1", "E2", "E3", "E5", "F1", "F2",
          "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11"]
    p1 = ["CTX-X1", "CTX-C7", "CTX-C10", "CTX-P1", "CTX-P2", "CMD-07", "CMD-08", "FB-02", "FB-04", "FB-11"]
    assert_ids("checklist.md", v1 + p1)
    text = read("checklist.md")
    assert "modules/mechanisms.md" in text and "Diátaxis" in text
    assert "Plans are neither checked nor recommended" in text


def test_checklist_names_scripts_and_their_limits() -> None:
    text = flat(read("checklist.md"))
    for s in ["instruction_inventory.py", "check_refs.py", "run_command.py", "prompt-audit",
              "itself calls removed"]:
        assert s in text


def test_skills_module_ids_and_formats() -> None:
    assert_ids("modules/skills.md", ["SK-01", "SK-03", "SK-05", "SK-06", "SK-10", "SK-14", "SK-17", "SK-18",
                                     "SK-20", "SP-13"])
    text = read("modules/skills.md")
    for h in ["Create", "Improve", "Install", "Disable", "skill-creator", "skill-doctor"]:
        assert h in text


def test_skills_module_uses_check_skills_with_manual_exemption() -> None:
    assert_ids("modules/skills.md", ["SK-02", "SK-07", "SK-12", "SK-13", "SK-15"])
    text = read("modules/skills.md")
    assert "check_skills.py" in text
    assert "disable-model-invocation: true" in text.split("## H2")[0]
    assert "${CLAUDE_SKILL_DIR}" in text


def test_skill_md_defines_skill_dir_and_links_thresholds() -> None:
    text = read("SKILL.md")
    assert "${CLAUDE_SKILL_DIR}" in text
    assert "`references/thresholds.md`" in text
    assert "`scripts/check_skills.py`" in text


def test_skill_sources_tiers_recipe_attribution() -> None:
    text = read("references/skill-sources.md")
    for s in ["claude plugin list --json --available", "Apache-2.0", "claude-automation-recommender",
              "Not carried over", "Memory MCP", "preview"]:
        assert s in text
    assert "Memory MCP" in text.split("## Not carried over")[1]


def test_mechanisms_module() -> None:
    assert_ids("modules/mechanisms.md", ["HK-01", "HK-02", "HK-03", "HK-06", "HK-07", "PRM-01", "PRM-02",
                                         "PRM-03", "PRM-07", "SUB-01", "SUB-03", "MCP-02", "MCP-06", "PLG-01"])
    text = read("modules/mechanisms.md")
    for s in ["stop_hook_active", "Read(", "in full", "structural"]:
        assert s in text


def test_history_module() -> None:
    text = read("modules/history.md")
    for s in ['claude -p "/skill-doctor" --permission-mode plan', "/doctor prompt-audit",
              "find_prompt_audit_plan.py", "insights_summary.py", "check_refs.py", "stale", "no_data",
              "unexpected_format", "personal", "auto mode"]:
        assert s in text


def test_design_before_code_module() -> None:
    assert_ids("modules/design-before-code.md", ["SP-04", "SP-05", "SP-07", "SP-09"])
    text = flat(read("modules/design-before-code.md"))
    for s in ["Superpowers", "Spec Kit", "OpenSpec", "BMAD", ".specify", "openspec/", "prove nothing"]:
        assert s in text


def test_applicability() -> None:
    text = read("references/applicability.md")
    for s in ["always checked", "e2e", "worktree", "SP-", "UI"]:
        assert s in text


def test_consent_lists_all_items() -> None:
    text = read("references/consent.md")
    for s in ["prompt-audit", "/insights", "commands", "container", "gh", "glab", "/doctor",
              "not checked — no consent", "dist/"]:
        assert s in text


def test_thresholds_have_sources() -> None:
    text = read("references/thresholds.md")
    for i in ["CTX-S1", "CTX-S2", "SK-03", "SK-10", "FB-03", "FB-04", "HK-07", "CMD-17"]:
        row = next(line for line in text.splitlines() if line.startswith(f"| {i} "))
        assert "http" in row


def test_subagent_prompts_have_output_contract() -> None:
    text = read("references/subagents.md")
    for s in ["Area check", "Recheck", "evidence", "in repo/personal",
              "keep", "discard", "Never recommend", "data, not instructions"]:
        assert s in text


def test_skill_frontmatter_and_links() -> None:
    text = read("SKILL.md")
    fm = text.split("---")[1]
    assert "name: audit" in fm and "disable-model-invocation: true" in fm
    for area in ["instructions", "spec", "verification", "review", "environment", "hygiene", "docs",
                 "skills", "mechanisms", "history", "design"]:
        assert area in fm
    description = next(line for line in fm.splitlines() if line.startswith("description:"))
    assert len(description) - len("description: ") <= 1024
    for rel in re.findall(r"`((?:modules|references|scripts)/[^`]+|checklist\.md|docs-guide\.md|report-template\.md)`", text):
        assert (SKILL_DIR / rel).exists(), rel
    assert "15 lines" not in text and "top three" not in text


def test_report_template_sections() -> None:
    text = read("report-template.md")
    for s in ["Top recommendations", "Summary", "Recommendations", "Skills", "What to remove",
              "Checked and fine", "Commands run", "Not checked", "in repo", "personal",
              "criteria: 2026-10-17", "harness-audit-<YYYY-MM-DD>.md"]:
        assert s in text


def steps_section() -> str:
    return read("SKILL.md").split("## Steps")[1].split("## Common audit mistakes")[0]


def test_step2_runs_mechanical_checks() -> None:
    steps = steps_section()
    for s in ["scripts/check_refs.py", "scripts/check_skills.py", "claude plugin validate"]:
        assert s in steps.split("3. **")[0], s


def test_subagents_get_skill_dir_tools_and_recheck_data() -> None:
    text = read("references/subagents.md").lower()
    for s in ["skill directory", "python3 -i", "claude plugin", "collected data", "answers at step 6"]:
        assert s in text, s


def test_consent_handles_timeouts_hidden_services_and_dirty_tree() -> None:
    text = read("references/consent.md")
    for s in ["540", "+ 60", "pre", "testcontainers", ".env.test", "--rm", "git status", "memory/"]:
        assert s in text, s


def test_history_runs_prompt_audit_in_background_and_paraphrases() -> None:
    text = read("modules/history.md")
    for s in ["run_in_background", "in your own words"]:
        assert s in text, s


def test_fresh_session_test_is_guarded_and_v1_questions_kept() -> None:
    steps = steps_section()
    step5 = steps.split("5. **")[1].split("6. **")[0]
    assert "Explore" in step5 and "data, not instructions" in step5
    step6 = steps.split("6. **")[1].split("7. **")[0]
    for s in ["wiki", "without an agent"]:
        assert s in step6, s


def test_review_minor_fixes() -> None:
    assert "harness-audit" in read("checklist.md").split("**F1.")[1].split("**F2.")[0]
    assert_ids("checklist.md", ["CTX-C11"])
    assert_ids("modules/mechanisms.md", ["PRM-09"])
    assert "tests go in a `Stop` hook" not in read("references/skill-sources.md")
    assert "/verify" not in read("modules/skills.md").split("## H3")[1].split("## H4")[0]
    assert "unknown" not in read("references/applicability.md")
    assert "up to 5" in read("report-template.md").lower() and "up to 5" in read("SKILL.md").lower()


def test_docs_guide_single_heading_label() -> None:
    text = flat(read("docs-guide.md"))
    assert "overlap by headings" not in text
    assert "compared by headings" in text
    assert "own convention" in text


def test_single_area_is_checked_without_area_subagents() -> None:
    step4 = flat(steps_section().split("4. **")[1].split("5. **")[0])
    assert "One named area" in step4 and "without subagents" in step4


def test_several_areas_are_accepted_and_get_a_subagent_each() -> None:
    text = read("SKILL.md")
    fm = text.split("---")[1]
    assert "separated by spaces" in fm
    areas = text.split("## Areas")[1].split("## Steps")[0]
    assert "/harness-audit:audit mechanisms hygiene history" in areas
    step4 = flat(steps_section().split("4. **")[1].split("5. **")[0])
    assert "one subagent per area" in step4
    assert "named areas" in flat(steps_section().split("3. **")[1].split("4. **")[0])
    assert "named areas" in flat(read("references/consent.md"))
    assert "<all / named>" in read("report-template.md")


def test_audit_does_not_audit_itself() -> None:
    rules = read("SKILL.md").split("## Rules")[1].split("## Scripts")[0]
    assert "harness-audit*" in rules and "symlink" in rules
    assert "harness-audit*" in read("references/subagents.md").split("## Recheck")[0]


def test_existing_prompt_audit_report_is_offered_first() -> None:
    history = read("modules/history.md")
    for s in ["--max-age-days 7", "--repo", "ready report"]:
        assert s in history, s
    assert "ready report" in read("references/consent.md")
    rules = read("SKILL.md").split("## Rules")[1].split("## Scripts")[0]
    assert "scripts/find_prompt_audit_plan.py" in rules


def test_specs_being_deleted_are_still_a_source_of_recorded_reasons() -> None:
    g5 = flat(read("checklist.md")).split("**G5.")[1].split("**G6.")[0]
    assert "is going to delete them" in g5 and "source" in g5
    docs = flat(read("report-template.md").split("## Documentation: target structure")[1])
    assert "evidence from code" not in docs and "where it came from" in docs.split("### Documentation rules")[0]


def test_docs_restructuring_is_one_recommendation_and_can_lead() -> None:
    step8 = flat(steps_section().split("8. **")[1])
    assert "from any area" in step8 and "Documentation restructuring is one recommendation" in step8
    assert "from any area" in read("report-template.md").split("## Top recommendations")[1].split("## Summary")[0]


def test_install_format_says_what_changes_for_the_person() -> None:
    install = read("modules/skills.md").split("### Install")[1].split("### Disable")[0]
    assert "What changes for you" in install
    template = read("report-template.md").split("### Install")[1].split("### Disable")[0]
    assert "what changes for you" in template


def test_area_subagents_do_not_read_session_transcripts() -> None:
    area = read("references/subagents.md").split("## Recheck")[0]
    assert "Do not read session records" in area and "~/.claude/projects" in area


def test_questions_have_no_fixed_cap_but_each_must_change_a_recommendation() -> None:
    step6 = flat(steps_section().split("6. **")[1].split("7. **")[0])
    assert "no more than five" not in step6
    assert "up to 4 at a time" in step6 and "changes a recommendation" in step6


def test_mcp_is_derived_from_the_person_not_from_a_fixed_list() -> None:
    assert_ids("modules/mechanisms.md", ["MCP-08", "MCP-03"])
    mcp = read("modules/mechanisms.md").split("## MCP")[1].split("## Plugins")[0]
    mcp08 = flat(mcp.split("**MCP-08.")[1])
    for s in ["need or a system from the stack", "/insights", "dependencies", "does not use",
              "What changes for you", "claude plugin list --json --available", "Checked and fine"]:
        assert s in mcp08, s
    for hardcoded in ["GitLab", "glab", "AWS", "Sentry", "Playwright"]:
        assert hardcoded not in mcp08, hardcoded
    deferred = next(line for line in mcp.splitlines() if "after calibration" in line)
    assert "MCP-08" not in deferred
    sources = read("references/skill-sources.md")
    assert "| Sign | MCP server |" not in sources and "GitLab MCP" not in sources
    network = read("references/consent.md").split("6. **Network")[1].split("7. **")[0]
    assert "MCP" in network


def test_running_subagents_are_not_killed_on_pause() -> None:
    step4 = flat(steps_section().split("4. **")[1].split("5. **")[0])
    for s in ["Do not stop running subagents", "SendMessage", "do not start it again"]:
        assert s in step4, s


def test_shared_files_go_to_subagents_as_a_digest_and_are_read_by_lines() -> None:
    step2 = steps_section().split("2. **")[1].split("3. **")[0]
    assert "Shared-files digest" in step2
    area = flat(read("references/subagents.md").split("## Recheck")[0])
    for s in ["The text of your items", "shared-files digest", "in full", "sed -n", "one command"]:
        assert s in area, s


def test_recheck_covers_only_findings_resting_on_read_text() -> None:
    step7 = flat(steps_section().split("7. **")[1].split("8. **")[0])
    for s in ["read text", "command output", "session data", "Never recommend"]:
        assert s in step7, s
    recheck = read("references/subagents.md").split("## Recheck")[1]
    assert "only findings resting on read text" in recheck


def test_subagents_inherit_the_session_model() -> None:
    assert "Do not set `model`" in flat(read("SKILL.md"))
    assert "inherit the model" in flat(read("references/subagents.md").split("## Area check")[0])


def h3_section() -> str:
    return flat(read("modules/skills.md").split("## H3")[1].split("## H4")[0])


def test_ready_skills_are_searched_from_needs_and_from_the_stack() -> None:
    h3 = h3_section()
    for s in ["need", "stack", "/insights", "What already exists", "find_skill_candidates.py", "--need",
              "stack_candidates", "project instructions", "SKILL.md", "covered by <what>"]:
        assert s in h3, s
    assert "no reason for a skill" not in h3


def test_a_fit_to_the_stack_is_enough_to_recommend() -> None:
    ranking = flat(read("references/skill-sources.md").split("## Ranking")[1].split('## "Sign')[0])
    assert "need or a fit to the stack" in ranking
    install = flat(read("modules/skills.md").split("### Install")[1].split("### Worth a look")[0])
    assert "dependency from the manifest" in install
    look = flat(read("modules/skills.md").split("### Worth a look")[1].split("### Disable")[0])
    assert "need or the stack" in look
    assert "need or stack" in flat(read("report-template.md").split("### Worth a look")[1])
    assert "stack_candidates" in read("references/skill-sources.md")


def test_skill_sources_have_no_ready_made_recommendations() -> None:
    sources = read("references/skill-sources.md")
    for gone in ["Almost any repository", "### Ready-made skills and plugins", "1,000 installs",
                 "pydantic-ai", "elastic/agent-skills"]:
        assert gone not in sources, gone


def test_source_tiers_cover_every_tier_of_the_script() -> None:
    sources = read("references/skill-sources.md")
    tiers = sources.split("## Source tiers")[1].split("## Search recipe")[0]
    for tier in ["`official`", "`vendor`", "`popular`", "`other`", "`not_checked`", "anthropic-plugin-directory",
                 "claude-plugins-official"]:
        assert tier in tiers, tier
    assert "--network" in sources and "package_skills" in sources


def test_popular_rule_in_documents_matches_the_script() -> None:
    script = load_script("find_skill_candidates")
    for rel in ["references/skill-sources.md", "references/thresholds.md"]:
        text = flat(read(rel))
        assert f"{script.MIN_STARS:,} stars" in text, rel
        assert f"{script.MAX_DAYS_SINCE_PUSH} days" in text, rel
        assert "archived" in text, rel


def test_popular_rule_warns_that_stars_belong_to_the_whole_repository() -> None:
    rule = flat(read("references/skill-sources.md").split('## The "Worth a look" rule')[1].split("## ")[0])
    for s in ["installs", "whole repository", "internal", "do not prove safety", "up to 5"]:
        assert s in rule, s


def test_worth_a_look_is_a_separate_format_without_install_command() -> None:
    module = flat(read("modules/skills.md").split("### Worth a look")[1].split("### Disable")[0])
    for s in ["up to 5", "What changes for you", "no full security check was done",
              "Do not print an install command"]:
        assert s in module, s
    template = flat(read("report-template.md").split("### Worth a look")[1].split("### Disable")[0])
    assert "up to 5" in template and "no full security check was done" in template


def test_consent_says_what_leaves_the_machine() -> None:
    consent = read("references/consent.md")
    item = flat(consent.split("6. **Network")[1].split("7. **")[0].replace("> ", ""))
    assert "skills.sh" in item and "Only general search words" in item
    rules = flat(consent.split("## Network")[1])
    assert "api.github.com" in rules and "private packages" in rules


def test_search_script_is_available_to_the_skills_area() -> None:
    skill = read("SKILL.md")
    table = skill.split("## Scripts")[1].split("## Areas")[0]
    assert "`scripts/find_skill_candidates.py`" in table and "--network" in table
    allowed = flat(skill.split("**Allowed without consent:**")[1].split("**Language.")[0])
    assert "find_skill_candidates.py" in allowed and "without `--network`" in allowed
    area = flat(read("references/subagents.md").split("## Recheck")[0])
    assert "find_skill_candidates.py" in area and "`--network` — only with consent" in area


def test_needs_that_appear_later_are_searched_after_step_4() -> None:
    step6 = flat(steps_section().split("6. **")[1].split("7. **")[0])
    assert "for the agent" in step6 and "find_skill_candidates.py" in step6


def test_mcp_search_uses_the_same_script() -> None:
    mcp08 = flat(read("modules/mechanisms.md").split("**MCP-08.")[1].split("The others (MCP-01")[0])
    assert "find_skill_candidates.py" in mcp08 and "Worth a look" in mcp08


def docs_template() -> str:
    return read("report-template.md").split("## Documentation: target structure")[1].split("## Fresh-session test")[0]


def test_working_alone_cancels_only_what_other_people_need() -> None:
    rules = flat(read("SKILL.md").split("## Rules")[1].split("## Scripts")[0])
    intro = flat(read("docs-guide.md").split("## 1.")[0])
    for text in (rules, intro):
        for s in ["work alone", "ADRs, a glossary, a PR template, `docs/README.md`", "CODEOWNERS", "onboarding",
                  "how-tos and references for readers without an agent"]:
            assert s in text, s
        assert "a table of contents for the team" not in text
    g_intro = flat(read("checklist.md").split("## G. Documentation")[1].split("**G1.")[0])
    assert "work alone" in g_intro and "`docs-guide.md`, introduction" in g_intro
    assert "CODEOWNERS" not in g_intro
    mistakes = flat(read("SKILL.md").split("## Common audit mistakes")[1])
    for s in ["minimal structure", "glossary", "PR template", "`docs/README.md`"]:
        assert s in mistakes, s


def test_recheck_keeps_what_the_agent_needs_when_working_alone() -> None:
    recheck = flat(read("references/subagents.md").split("## Recheck")[1])
    for s in ["Questions 3 and 6 never discard", "works alone", "(G5, G6)", "(G12)", "(G9, G11)", "`docs/README.md`",
              "CODEOWNERS"]:
        assert s in recheck, s


def adr_section() -> str:
    return flat(read("docs-guide.md").split("## 4. ADRs")[1].split("## 5.")[0])


def test_audit_proposes_the_adr_practice_and_people_write_adrs_after_it() -> None:
    adr = adr_section()
    for s in ["**Always.**", "does not invent ADRs", "after the audit", "`docs/decisions/`",
              "`docs/decisions/0000-template.md`", "even in a small project", "superseded by NNNN",
              "a decision with alternatives gets an ADR"]:
        assert s in adr, s
    for gone in ["Where to get candidates", "reason not recorded", "candidates per report", "threshold G6"]:
        assert gone not in adr, gone
    g6 = flat(read("checklist.md").split("**G6.")[1].split("**G7.")[0])
    for s in ["section 4", "no reason to skip G6", "invents no ADRs", "under G5", "one example ADR",
              "CTX-D3"]:
        assert s in g6, s
    assert "Candidates" not in g6
    step6 = flat(steps_section().split("6. **")[1].split("7. **")[0])
    assert "ADR candidates" not in step6 and "<obvious alternative>" not in step6
    template = flat(docs_template().split("### Documentation rules")[0])
    for s in ["what ADRs give this project", "the template", "one example ADR", "placeholders",
              "the line for the root `CLAUDE.md`"]:
        assert s in template, s
    assert "Proposed ADRs" not in template
    mistakes = flat(read("SKILL.md").split("## Common audit mistakes")[1])
    assert "Inventing ADRs" in mistakes and "Leaving decisions recorded in specs for later" in mistakes
    assert "| G6 " not in read("references/thresholds.md")


def test_report_explains_what_adrs_give() -> None:
    adr = adr_section()
    give = adr.split("**What ADRs give")[1].split("**What the audit does")[0]
    for s in ["blindly preserves", "the agent reads the reason", "the next developer", "superseded"]:
        assert s in give, s


def test_example_adr_is_one_real_decision_with_placeholders_for_what_is_unknown() -> None:
    adr = adr_section()
    for s in ["one example ADR", "most architecturally significant", "how much code and data", "NoSQL client",
              "docker-compose", "only what the repository says", "<why this option: fill in>", "the template alone"]:
        assert s in adr, s


def test_adr_template_text_is_in_the_guide() -> None:
    template = read("docs-guide.md").split("### ADR template")[1].split("## 5.")[0]
    for s in ["# NNNN.", "- Status:", "## Context", "## Decision", "We will", "## Consequences"]:
        assert s in template, s


def test_deleted_specs_get_a_transfer_table_instead_of_an_archive() -> None:
    g5 = flat(read("checklist.md").split("**G5.")[1].split("**G6.")[0])
    for s in ["do not propose `docs/archive/`", "| Spec | ADRs from it", "then deletion, in one PR"]:
        assert s in g5, s
    template = flat(docs_template())
    assert "| Spec | ADRs from it" in template and "in one PR" in template


def test_specs_are_moved_and_deleted_one_pr_per_spec() -> None:
    g5 = flat(read("checklist.md").split("**G5.")[1].split("**G6.")[0])
    template = flat(docs_template())
    for text in (g5, template):
        assert "in one PR per spec" in text and "different specs go in different PRs" in text


def test_target_structure_is_drawn_as_a_mermaid_diagram() -> None:
    guide = flat(read("docs-guide.md").split("## 6.")[1].split("## 7.")[0])
    for s in ["Mermaid", "`subgraph`", "`classDef`", "node threshold", "Always in context", "On demand", "Reference",
              "Decisions", "What disappears"]:
        assert s in guide, s
    template = docs_template()
    tree = template.index("<target tree")
    diagram = template.index("```mermaid")
    assert tree < diagram
    for s in ["subgraph always[Always in context]", "subgraph decisions[Decisions]", "classDef new",
              "classDef moved"]:
        assert s in template, s


def test_mermaid_example_sets_a_text_colour_for_dark_themes() -> None:
    class_defs = [line for line in docs_template().splitlines() if line.strip().startswith("classDef")]
    assert class_defs
    for line in class_defs:
        assert "fill:" in line and "color:" in line, line


def test_glossary_has_a_place_a_check_and_a_report_slot() -> None:
    assert_ids("checklist.md", ["G12"])
    guide = flat(read("docs-guide.md").split("## 2.")[1].split("## 3.")[0])
    for s in ["`glossary.md`", "where in the code", "which word not to use"]:
        assert s in guide, s
    g12 = flat(read("checklist.md").split("**G12.")[1])
    for s in ["Always", "whatever the number of terms", "one word per concept", "stage and size",
              "No terms found", "`docs/glossary.md` — read before naming a new domain thing", "enums"]:
        assert s in g12, s
    for gone in ["threshold G12", "fewer such terms", "Do not propose it"]:
        assert gone not in g12, gone
    template = flat(docs_template().split("### Documentation rules")[0])
    for s in ["Glossary: always", "`file:line`", "stage and size"]:
        assert s in template, s
    assert "why a glossary is not needed" not in template


def test_type_folders_appear_with_their_first_document() -> None:
    guide = flat(read("docs-guide.md").split("## 2.")[1].split("## 3.")[0])
    for s in ["Folders by type from the first document", "there is no flat `docs/`", "`docs/<area>/…`",
              "Folders that do not exist yet", "`how-to/` —", "`reference/` —", "`explanation/` —"]:
        assert s in guide, s
    for gone in ["all three", "will not grow", "document threshold", "In a flat `docs/`", "small project"]:
        assert gone not in guide, gone
    proposal = flat(read("docs-guide.md").split("## 6.")[1].split("## 7.")[0])
    assert "flat `docs/`" not in proposal and "folders that do not exist yet" in proposal
    template = flat(docs_template())
    assert "Structure chosen" in template and "Folders for later" in template
    assert "flat `docs/`" not in template
    consent = flat(read("references/consent.md"))
    assert "Will the project grow" not in consent and "flat" not in consent


def test_target_tree_shows_the_new_documents_the_audit_proposes() -> None:
    g10 = flat(read("checklist.md").split("**G10.")[1].split("**G11.")[0])
    assert "only existing content" not in g10
    for s in ["ADRs from specs", "the glossary", 'marked "new"']:
        assert s in g10, s
    proposal = flat(read("docs-guide.md").split("## 6.")[1].split("## 7.")[0])
    assert "existing content only" not in proposal
    assert "the new documents of G5, G6, G7 and G12" in proposal


def test_pr_template_is_always_proposed_when_there_is_a_remote() -> None:
    guide = flat(read("docs-guide.md").split("## 7.")[1].split("## Sources")[0])
    for s in ["`git remote -v`", "`.github/pull_request_template.md`",
              "`.gitlab/merge_request_templates/Default.md`", "`git check-ignore`", "`gh pr create --body`",
              "~15 lines", "A PR description fills `.github/pull_request_template.md`.", "## Verified"]:
        assert s in guide, s
    checklist = flat(read("checklist.md"))
    for item, end in [("**G9.", "**G10."), ("**G11.", "**G12.")]:
        text = checklist.split(item)[1].split(end)[0]
        assert "section 7" in text and "work alone" in text, item
    rules = flat(docs_template().split("### Documentation rules")[1])
    assert "always" in rules and "PR/MR template" in rules and "full text" in rules
    allowed = flat(read("SKILL.md").split("**Allowed without consent:**")[1].split("**Language.")[0])
    assert "remote -v" in allowed


def test_secrets_from_remote_urls_never_reach_the_report() -> None:
    rules = flat(read("SKILL.md").split("## Rules")[1].split("## Scripts")[0])
    assert "Never copy a secret into the report" in rules and "only the host" in rules
    area = flat(read("references/subagents.md").split("## Area check")[1].split("## Recheck")[0])
    assert "Never copy a secret" in area and "only the host" in area
    guide = flat(read("docs-guide.md").split("## 7.")[1].split("## Sources")[0])
    assert "only the host" in guide and "never the full URL" in guide


def test_existing_adr_glossary_and_template_are_found_before_proposing_new_ones() -> None:
    adr = adr_section()
    assert "`doc/adr/`" in adr and "continue its numbering" in adr
    g6 = flat(read("checklist.md").split("**G6.")[1].split("**G7.")[0])
    assert "the project's ADR folder" in g6
    guide = flat(read("docs-guide.md").split("## 7.")[1].split("## Sources")[0])
    assert "git ls-files | grep -iE 'pull_request_template|merge_request_templates/'" in guide
    g12 = flat(read("checklist.md").split("**G12.")[1])
    assert "`git ls-files | grep -i glossary`" in g12


def test_pr_template_is_not_limited_to_github_and_gitlab_com() -> None:
    guide = flat(read("docs-guide.md").split("## 7.")[1].split("## Sources")[0])
    for s in ["self-hosted GitLab", "`.gitlab-ci.yml`", "a host other than GitHub or GitLab"]:
        assert s in guide, s
    assert "remote on GitHub or GitLab" not in guide
    g9 = flat(read("checklist.md").split("**G9.")[1].split("**G10.")[0])
    assert "GitHub or GitLab" not in g9
    assert "GitHub or GitLab remote" not in flat(docs_template())


def test_documentation_thresholds_live_only_in_thresholds_md() -> None:
    thresholds = read("references/thresholds.md").splitlines()
    g10 = next(line for line in thresholds if line.startswith("| G10 "))
    assert "~25 nodes" in g10 and "flat" not in g10
    assert not any(line.startswith("| G12 ") for line in thresholds)
    g_area = flat(read("checklist.md").split("## G. Documentation")[1])
    guide = flat(read("docs-guide.md"))
    template = flat(docs_template())
    for text in (g_area, guide, template):
        for number in ["3–5", "~10", "~25", "at least 5", "fewer than 5", "about ten"]:
            assert number not in text, number


def test_decisions_recorded_in_specs_become_adrs_during_the_audit() -> None:
    adr = adr_section()
    transfer = adr.split("**Transferring decisions from specs.**")[1].split("### ADR template")[0]
    for s in ["kept or about to be deleted", "Considered and Rejected", "one ADR in full", "accepted",
              "stands on its own", "in the order the decisions were made", "is not added"]:
        assert s in transfer, s
    g5 = flat(read("checklist.md").split("**G5.")[1].split("**G6.")[0])
    for s in ["become ADRs during the audit", "full text", "whether the spec is kept or deleted"]:
        assert s in g5, s
    template = flat(docs_template().split("### Documentation rules")[0])
    assert "ADRs from specs" in template and "the full text of each" in template


def test_pr_template_is_one_recommendation_under_g11_that_respects_an_existing_one() -> None:
    checklist = flat(read("checklist.md"))
    g9 = checklist.split("**G9.")[1].split("**G10.")[0]
    g11 = checklist.split("**G11.")[1].split("**G12.")[0]
    assert "G11's recommendation" in g9 and "only note whether it exists" in g9
    assert "proposed whenever" not in g9
    for s in ["if there is no template", "what to change if there is one", "not under G9"]:
        assert s in g11, s
    assert "always, even if the rules are complete" not in g11


def test_documentation_questions_are_asked_with_consent_before_the_checks() -> None:
    consent = flat(read("references/consent.md"))
    for s in ["What do you do with specs and design docs after implementation", "only if area G is checked",
              "found specs or design docs", "Open questions"]:
        assert s in consent, s
    step3 = flat(steps_section().split("3. **")[1].split("4. **")[0])
    assert "documentation questions" in step3
    step4 = flat(steps_section().split("4. **")[1].split("5. **")[0])
    assert "answers to the documentation questions" in step4
    step6 = flat(steps_section().split("6. **")[1].split("7. **")[0])
    assert "What do you do with specs" not in step6 and "Will the project grow" not in step6
    assert "asked at step 3" in step6
    area = flat(read("references/subagents.md").split("## Area check")[1].split("## Recheck")[0])
    assert "answers to the step 3 questions" in area
    recheck = flat(read("references/subagents.md").split("## Recheck")[1])
    assert "answers at step 3 or step 6" in recheck and "Answers at step 3:" in recheck
    g5 = flat(read("checklist.md").split("**G5.")[1].split("**G6.")[0])
    assert "answer at step 3" in g5 and "step 6" not in g5
    assert "(step 3)" in flat(docs_template()) and "(step 6)" not in flat(docs_template())
