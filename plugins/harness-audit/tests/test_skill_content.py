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
    for s in ["ADR", "wiki", "without an agent"]:
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


def test_adr_candidates_come_from_specs_docs_code_or_the_person() -> None:
    checklist = flat(read("checklist.md"))
    g5 = checklist.split("**G5.")[1].split("**G6.")[0]
    assert "is going to delete them" in g5 and "source" in g5
    g6 = checklist.split("**G6.")[1].split("**G7.")[0]
    for s in ["existing", "step 6", "starting one"]:
        assert s in g6, s
    adr = flat(read("docs-guide.md").split("## 4. When an ADR is needed")[1].split("## 5.")[0])
    for s in ["Where to get candidates", "design doc", "docs/decisions/", "keeping ADRs"]:
        assert s in adr, s
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
