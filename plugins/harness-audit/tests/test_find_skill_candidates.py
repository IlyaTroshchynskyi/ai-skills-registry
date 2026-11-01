from __future__ import annotations

import http.client
import json
import subprocess
import sys
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from helpers import SCRIPTS_DIR, load_script

NOW = datetime(2026, 10, 31, tzinfo=timezone.utc)
DIRECTORY = "anthropic-plugin-directory"


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    return load_script("find_skill_candidates")


def pushed(days: int) -> str:
    return (NOW - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_info(stars: int, days: int, archived: bool = False, license_id: str | None = "MIT") -> dict[str, Any]:
    return {
        "stargazers_count": stars,
        "pushed_at": pushed(days),
        "archived": archived,
        "license": {"spdx_id": license_id} if license_id else None,
    }


def plugin(name: str, url: str | None = None, marketplace: str = DIRECTORY, description: str = "",
           installs: int | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "pluginId": f"{name}@{marketplace}",
        "name": name,
        "marketplaceName": marketplace,
        "description": description,
        "source": {"source": "url", "url": url} if url else "./plugins/" + name,
    }
    if installs is not None:
        item["installCount"] = installs
    return item


def catalog(*plugins: dict[str, Any], installed: tuple[str, ...] = ()) -> dict[str, Any]:
    return {"installed": [{"id": i} for i in installed], "available": list(plugins)}


class Stub:
    """Network stand-in: skills.sh and GitHub answer from dictionaries, every call is recorded."""

    def __init__(self, mod: ModuleType, skills: list[dict[str, Any]] | None = None,
                 repos: dict[str, Any] | None = None) -> None:
        self.mod, self.skills, self.repos = mod, skills or [], repos or {}
        self.calls: list[str] = []

    def __call__(self, url: str) -> Any:
        self.calls.append(url)
        if url.startswith(self.mod.SKILLS_SH_URL):
            return {"skills": self.skills}
        result = self.repos[url.removeprefix(self.mod.GITHUB_REPO_URL)]
        if isinstance(result, Exception):
            raise result
        return result

    def github_calls(self) -> list[str]:
        return [c for c in self.calls if c.startswith(self.mod.GITHUB_REPO_URL)]


def skill(source: str, skill_id: str, installs: int = 100) -> dict[str, Any]:
    return {"id": f"{source}/{skill_id}", "source": source, "skillId": skill_id, "name": skill_id, "installs": installs}


def candidates(result: dict[str, Any], index: int = 0) -> dict[str, dict[str, Any]]:
    return {c["name"]: c for c in result["needs"][index]["candidates"]}


@pytest.mark.parametrize("url, expected", [
    ("git+https://github.com/TanStack/query.git", "TanStack/query"),
    ("https://github.com/vitest-dev/vitest/tree/main/packages/vitest", "vitest-dev/vitest"),
    ("git@github.com:microsoft/playwright.git", "microsoft/playwright"),
    ("github:expressjs/express", "expressjs/express"),
    ("expressjs/express", "expressjs/express"),
    ("https://github.com/owner/repo.name.git", "owner/repo.name"),
    ("https://gitlab.com/owner/repo", None),
    ("gitlab:owner/repo", None),
    ("./plugins/local", None),
    ("https://github.com/sponsors/somebody", None),
    ("", None),
])
def test_github_repo_reads_every_form_of_repository_field(mod: ModuleType, url: str, expected: str | None) -> None:
    assert mod.github_repo(url) == expected


def write_package(root: Path, dep: str, repository: Any) -> None:
    folder = root / "node_modules" / dep
    folder.mkdir(parents=True)
    (folder / "package.json").write_text(json.dumps({"name": dep, "repository": repository}))


def test_vendor_is_taken_from_installed_package_manifest(tmp_path: Path, mod: ModuleType) -> None:
    (tmp_path / "package.json").write_text(json.dumps({
        "dependencies": {"@tanstack/react-query": "5"}, "devDependencies": {"vitest": "3"}}))
    write_package(tmp_path, "@tanstack/react-query", {"url": "git+https://github.com/TanStack/query.git"})
    write_package(tmp_path, "vitest", "https://github.com/vitest-dev/vitest")
    vendors, unknown = mod.find_vendors(tmp_path)
    assert vendors == {"tanstack": ["@tanstack/react-query"], "vitest-dev": ["vitest"]}
    assert unknown == 0


def test_vendor_ignores_type_stubs_and_counts_what_is_not_installed(tmp_path: Path, mod: ModuleType) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"@types/node": "1", "left-pad": "1"}}))
    vendors, unknown = mod.find_vendors(tmp_path)
    assert vendors == {} and unknown == 1


def test_vendor_finds_packages_hoisted_to_the_workspace_root(tmp_path: Path, mod: ModuleType) -> None:
    app = tmp_path / "apps" / "web"
    app.mkdir(parents=True)
    (app / "package.json").write_text(json.dumps({"dependencies": {"zod": "4"}}))
    write_package(tmp_path, "zod", "https://github.com/colinhacks/zod")
    assert mod.find_vendors(tmp_path)[0] == {"colinhacks": ["zod"]}


def test_vendor_skips_worktrees_and_manifests_inside_node_modules(tmp_path: Path, mod: ModuleType) -> None:
    worktree = tmp_path / ".claude" / "worktrees" / "x"
    worktree.mkdir(parents=True)
    (worktree / "package.json").write_text(json.dumps({"dependencies": {"a": "1"}}))
    write_package(tmp_path, "b", "https://github.com/owner/b")
    assert mod.find_vendors(tmp_path) == ({}, 0)


def test_vendor_reads_python_metadata_from_virtualenv(tmp_path: Path, mod: ModuleType) -> None:
    info = tmp_path / ".venv" / "lib" / "python3.12" / "site-packages" / "crewai-1.0.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: crewai\n"
        "Project-URL: Funding, https://github.com/sponsors/someone\n"
        "Project-URL: Source, https://github.com/crewAIInc/crewAI\n"
        "\nBody mentions https://github.com/other/project\n")
    assert mod.find_vendors(tmp_path)[0] == {"crewaiinc": ["crewai"]}


def write_python_package(root: Path, name: str, repository: str) -> None:
    info = root / ".venv" / "lib" / "python3.12" / "site-packages" / f"{name}-1.0.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(f"Name: {name}\nHome-page: {repository}\n")


def test_vendor_keeps_only_direct_python_dependencies(tmp_path: Path, mod: ModuleType) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["crewai[tools]>=1.0", "Pydantic_Settings~=2"]\n')
    write_python_package(tmp_path, "crewai", "https://github.com/crewAIInc/crewAI")
    write_python_package(tmp_path, "pydantic-settings", "https://github.com/pydantic/pydantic-settings")
    write_python_package(tmp_path, "mcp", "https://github.com/modelcontextprotocol/python-sdk")
    assert mod.find_vendors(tmp_path)[0] == {"crewaiinc": ["crewai"], "pydantic": ["pydantic-settings"]}


def test_vendor_finds_python_manifest_in_a_subfolder(tmp_path: Path, mod: ModuleType) -> None:
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "requirements.txt").write_text("fastapi==0.1\n")
    write_python_package(tmp_path, "fastapi", "https://github.com/fastapi/fastapi")
    write_python_package(tmp_path, "starlette", "https://github.com/encode/starlette")
    assert mod.find_vendors(tmp_path)[0] == {"fastapi": ["fastapi"]}


def test_vendor_reads_direct_requirements_from_go_mod(tmp_path: Path, mod: ModuleType) -> None:
    (tmp_path / "go.mod").write_text(
        "module github.com/me/app\n\nrequire (\n"
        "\tgithub.com/gin-gonic/gin v1.9.0\n"
        "\tgithub.com/some/transitive v1.0.0 // indirect\n)\n")
    assert mod.find_vendors(tmp_path)[0] == {"gin-gonic": ["github.com/gin-gonic/gin"]}


def test_package_skills_are_listed_with_their_frontmatter(tmp_path: Path, mod: ModuleType) -> None:
    folder = tmp_path / "e2e" / "node_modules" / "playwright-core" / "skill"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text("---\nname: playwright-cli\ndescription: Automate browsers.\n---\n# Body\n")
    assert mod.find_package_skills(tmp_path) == [{
        "path": "e2e/node_modules/playwright-core/skill/SKILL.md",
        "name": "playwright-cli",
        "description": "Automate browsers.",
    }]


def test_catalog_search_needs_every_word_of_the_query(mod: ModuleType) -> None:
    data = catalog(plugin("a", description="Mutation testing for code"), plugin("b", description="Testing of forms"))
    assert [c["name"] for c in mod.search_catalog(data, "mutation testing")] == ["a"]


def test_catalog_search_matches_whole_words_in_name_or_description(mod: ModuleType) -> None:
    data = catalog(plugin("stryker-tools"), plugin("other", description="Semantic + lexicalized search"),
                   plugin("third", description=None))
    assert [c["name"] for c in mod.search_catalog(data, "stryker")] == ["stryker-tools"]
    assert mod.search_catalog(data, "lexical") == []


def test_catalog_search_skips_installed_plugins(mod: ModuleType) -> None:
    data = catalog(plugin("superpowers", description="testing"), installed=("superpowers@superpowers-marketplace",))
    assert mod.search_catalog(data, "testing") == []


def test_catalog_search_prefers_official_entry_of_a_duplicate(mod: ModuleType) -> None:
    data = catalog(plugin("dup", "https://github.com/x/dup", description="testing"),
                   plugin("dup", marketplace=mod.OFFICIAL_MARKETPLACE, description="testing", installs=7))
    assert [(c["marketplace"], c["installs"]) for c in mod.search_catalog(data, "testing")] == [
        (mod.OFFICIAL_MARKETPLACE, 7)]


def test_catalog_search_reads_git_subdir_and_shortens_description(mod: ModuleType) -> None:
    item = plugin("a", description="testing " + "x" * 500)
    item["source"] = {"source": "git-subdir", "url": "https://github.com/anthropics/plugins", "path": "plugins/a"}
    found = mod.search_catalog(catalog(item), "testing")[0]
    assert found["repo"] == "anthropics/plugins" and len(found["description"]) <= mod.DESCRIPTION_LIMIT


@pytest.mark.parametrize("info, expected", [
    (repo_info(3000, 180), True),
    (repo_info(2999, 1), False),
    (repo_info(3000, 181), False),
    (repo_info(9000, 1, archived=True), False),
    ({"stargazers_count": 9000}, False),
    (repo_info(7909, 2, license_id=None), True),
])
def test_popular_rule_is_stars_recent_push_and_not_archived(
        mod: ModuleType, info: dict[str, Any], expected: bool) -> None:
    assert mod.is_popular(info, NOW) is expected


@pytest.mark.parametrize("stars, days, expected", [
    (307885, 0, True), (33285, 2, True), (7909, 2, True), (6028, 0, True),
    (1091, 22, False), (413, 102, False), (228, 51, False), (220, 76, False), (36, 272, False),
])
def test_popular_rule_on_real_repositories_from_the_calibration(
        mod: ModuleType, stars: int, days: int, expected: bool) -> None:
    assert mod.is_popular(repo_info(stars, days), NOW) is expected


@pytest.mark.parametrize("repo", ["github/awesome-copilot", "someone/Awesome-Claude-Skills"])
def test_awesome_list_is_not_popular_whatever_its_stars(mod: ModuleType, repo: str) -> None:
    assert mod.classify({"repo": repo, "marketplace": None}, {}, repo_info(40619, 1), NOW) == "other"


def test_look_alike_owner_is_not_the_vendor_whatever_its_installs(mod: ModuleType) -> None:
    item = {"repo": "tanstack-skills/tanstack-skills", "marketplace": None, "installs": 10062}
    assert mod.classify(item, {"tanstack": ["@tanstack/react-query"]}, repo_info(36, 272), NOW) == "other"


@pytest.mark.parametrize("item, info, expected", [
    ({"repo": None, "marketplace": "claude-plugins-official"}, None, "official"),
    ({"repo": "anthropics/skills", "marketplace": None}, None, "official"),
    ({"repo": "Aws/agent-toolkit", "marketplace": DIRECTORY}, None, "vendor"),
    ({"repo": "trailofbits/skills", "marketplace": None}, repo_info(7909, 2), "popular"),
    ({"repo": "someone/skills", "marketplace": None}, repo_info(10, 2), "other"),
    ({"repo": "someone/skills", "marketplace": DIRECTORY}, None, "not_checked"),
    ({"repo": None, "marketplace": "claude-code-skills"}, None, "not_checked"),
])
def test_classify_gives_the_tier(mod: ModuleType, item: dict[str, Any], info: Any, expected: str) -> None:
    assert mod.classify(item, {"aws": ["@aws-sdk/client"]}, info, NOW) == expected


def test_without_network_nothing_is_fetched_and_third_party_stays_unchecked(mod: ModuleType) -> None:
    data = catalog(plugin("vendor-one", "https://github.com/aws/x", description="testing"),
                   plugin("third", "https://github.com/someone/x", description="testing"))
    result = mod.collect(data, {"aws": ["a"]}, ["testing"], NOW)
    assert list(candidates(result)) == ["vendor-one"]
    assert result["needs"][0]["not_checked"] == ["third"]
    assert result["errors"] == []


def test_network_merges_registry_and_checks_only_third_party_on_github(mod: ModuleType) -> None:
    data = catalog(plugin("vendor-one", "https://github.com/aws/x", description="testing"))
    stub = Stub(mod, skills=[skill("trailofbits/skills", "mutation-testing", 4399),
                             skill("tanstack-skills/tanstack-skills", "tanstack-query", 10062)],
                repos={"trailofbits/skills": repo_info(7909, 2, license_id="CC-BY-SA-4.0"),
                       "tanstack-skills/tanstack-skills": repo_info(36, 272)})
    result = mod.collect(data, {"aws": ["a"]}, ["testing"], NOW, stub)
    found = candidates(result)
    assert list(found) == ["vendor-one", "mutation-testing"]
    assert found["mutation-testing"]["tier"] == "popular"
    assert found["mutation-testing"]["stars"] == 7909
    assert found["mutation-testing"]["days_since_push"] == 2
    assert found["mutation-testing"]["license"] == "CC-BY-SA-4.0"
    assert result["needs"][0]["dropped"] == 1
    assert len(stub.github_calls()) == 2


def test_candidates_are_ordered_by_tier_then_installs(mod: ModuleType) -> None:
    data = catalog(plugin("low", "https://github.com/anthropics/a", description="testing", installs=1),
                   plugin("high", "https://github.com/anthropics/b", description="testing", installs=9),
                   plugin("vendor-one", "https://github.com/aws/x", description="testing", installs=99999))
    stub = Stub(mod, skills=[skill("big/skills", "pop", 500000)], repos={"big/skills": repo_info(5000, 1)})
    result = mod.collect(data, {"aws": ["a"]}, ["testing"], NOW, stub)
    assert [c["name"] for c in result["needs"][0]["candidates"]] == ["high", "low", "vendor-one", "pop"]


def test_candidates_per_need_are_capped(mod: ModuleType) -> None:
    plugins = [plugin(f"p{i}", marketplace=mod.OFFICIAL_MARKETPLACE, description="testing") for i in range(20)]
    result = mod.collect(catalog(*plugins), {}, ["testing"], NOW)
    assert len(result["needs"][0]["candidates"]) == mod.MAX_CANDIDATES_PER_NEED


def test_repository_is_checked_once_across_needs(mod: ModuleType) -> None:
    stub = Stub(mod, skills=[skill("big/skills", "pop")], repos={"big/skills": repo_info(5000, 1)})
    mod.collect(catalog(), {}, ["one", "two"], NOW, stub)
    assert len(stub.github_calls()) == 1


def test_lookups_per_need_are_limited_and_the_rest_stays_unchecked(mod: ModuleType) -> None:
    total = mod.MAX_GITHUB_LOOKUPS_PER_NEED + 3
    stub = Stub(mod, skills=[skill(f"o{i}/r", f"s{i}", total - i) for i in range(total)],
                repos={f"o{i}/r": repo_info(10, 1) for i in range(total)})
    result = mod.collect(catalog(), {}, ["testing"], NOW, stub)
    assert len(stub.github_calls()) == mod.MAX_GITHUB_LOOKUPS_PER_NEED
    assert result["needs"][0]["not_checked"] == [f"s{i}" for i in range(mod.MAX_GITHUB_LOOKUPS_PER_NEED, total)]


class ByQuery(Stub):
    """skills.sh answers each query with its own list."""

    def __init__(self, mod: ModuleType, by_query: dict[str, list[dict[str, Any]]], repos: dict[str, Any]) -> None:
        super().__init__(mod, repos=repos)
        self.by_query = by_query

    def __call__(self, url: str) -> Any:
        if url.startswith(self.mod.SKILLS_SH_URL):
            self.calls.append(url)
            return {"skills": self.by_query[url.split("q=")[1].split("&")[0]]}
        return super().__call__(url)


def test_first_need_does_not_starve_the_next_one(mod: ModuleType) -> None:
    many = [skill(f"o{i}/r", f"s{i}") for i in range(mod.MAX_GITHUB_LOOKUPS)]
    repos = {f"o{i}/r": repo_info(10, 1) for i in range(mod.MAX_GITHUB_LOOKUPS)} | {"big/r": repo_info(5000, 1)}
    stub = ByQuery(mod, {"first": many, "second": [skill("big/r", "wanted")]}, repos)
    result = mod.collect(catalog(), {}, ["first", "second"], NOW, stub)
    assert list(candidates(result, 1)) == ["wanted"]


def test_lookups_of_a_whole_run_stay_under_the_anonymous_github_limit(mod: ModuleType) -> None:
    per_need = mod.MAX_GITHUB_LOOKUPS_PER_NEED
    needs = [f"need{n}" for n in range(mod.MAX_GITHUB_LOOKUPS // per_need + 2)]
    by_query = {need: [skill(f"{need}-{i}/r", f"{need}-{i}") for i in range(per_need)] for need in needs}
    repos = {item["source"]: repo_info(10, 1) for items in by_query.values() for item in items}
    stub = ByQuery(mod, by_query, repos)
    mod.collect(catalog(), {}, needs, NOW, stub)
    assert len(stub.github_calls()) == mod.MAX_GITHUB_LOOKUPS < 60


def test_cached_repository_does_not_use_up_the_share_of_a_need(mod: ModuleType) -> None:
    shared = [skill("big/r", f"s{i}") for i in range(mod.MAX_GITHUB_LOOKUPS_PER_NEED + 2)]
    stub = Stub(mod, skills=shared, repos={"big/r": repo_info(5000, 1)})
    result = mod.collect(catalog(), {}, ["testing"], NOW, stub)
    assert result["needs"][0]["not_checked"] == [] and len(stub.github_calls()) == 1


def test_rate_limit_stops_github_lookups_and_is_reported_once(mod: ModuleType) -> None:
    limited = urllib.error.HTTPError("u", 403, "rate limit", None, None)  # type: ignore[arg-type]
    stub = Stub(mod, skills=[skill("a/r", "s1", 2), skill("b/r", "s2", 1)], repos={"a/r": limited, "b/r": limited})
    result = mod.collect(catalog(), {}, ["testing"], NOW, stub)
    assert len(stub.github_calls()) == 1
    assert result["needs"][0]["not_checked"] == ["s1", "s2"]
    assert len(result["errors"]) == 1 and "GitHub" in result["errors"][0]


def test_missing_repository_does_not_stop_the_others(mod: ModuleType) -> None:
    gone = urllib.error.HTTPError("u", 404, "not found", None, None)  # type: ignore[arg-type]
    stub = Stub(mod, skills=[skill("a/r", "gone-one", 2), skill("b/r", "fine", 1)],
                repos={"a/r": gone, "b/r": repo_info(5000, 1)})
    result = mod.collect(catalog(), {}, ["testing"], NOW, stub)
    assert list(candidates(result)) == ["fine"]
    assert result["needs"][0]["not_checked"] == ["gone-one"]


def test_registry_failure_keeps_catalog_results(mod: ModuleType) -> None:
    def broken(url: str) -> Any:
        raise urllib.error.URLError("no route")

    data = catalog(plugin("official-one", marketplace=mod.OFFICIAL_MARKETPLACE, description="testing"))
    result = mod.collect(data, {}, ["testing"], NOW, broken)
    assert list(candidates(result)) == ["official-one"]
    assert len(result["errors"]) == 1 and "skills.sh" in result["errors"][0]


def test_unexpected_registry_answer_is_ignored(mod: ModuleType) -> None:
    result = mod.collect(catalog(), {}, ["testing"], NOW, lambda url: {"skills": [{"source": 5}, "junk"]})
    assert result["needs"][0]["candidates"] == []


def test_installs_of_unexpected_type_do_not_break_sorting(mod: ModuleType) -> None:
    items = [{"source": "a/r", "skillId": "text", "installs": "many"}, skill("b/r", "number", 5)]
    stub = Stub(mod, skills=items, repos={"a/r": repo_info(5000, 1), "b/r": repo_info(5000, 1)})
    result = mod.collect(catalog(), {}, ["testing"], NOW, stub)
    assert [c["name"] for c in result["needs"][0]["candidates"]] == ["number", "text"]


def test_broken_response_is_reported_like_a_network_error(mod: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: Any, **kwargs: Any) -> Any:
        raise http.client.IncompleteRead(b"")

    monkeypatch.setattr(mod.urllib.request, "urlopen", broken)
    result = mod.collect(catalog(), {}, ["testing"], NOW, mod.fetch_json)
    assert len(result["errors"]) == 1 and "skills.sh" in result["errors"][0]


def test_query_is_encoded_for_the_registry(mod: ModuleType) -> None:
    stub = Stub(mod)
    mod.collect(catalog(), {}, ["e2e failures & flaky"], NOW, stub)
    assert "q=e2e+failures+%26+flaky" in stub.calls[0]


def test_stack_lists_vendor_plugin_for_a_scoped_dependency(mod: ModuleType) -> None:
    data = catalog(plugin("aws-core", "https://github.com/aws/toolkit", description="AWS"),
                   plugin("third", "https://github.com/someone/x"))
    found = mod.find_stack_candidates(data, {"aws": ["@aws-sdk/client-s3"]})
    assert [(c["name"], c["tier"], c["dependencies"]) for c in found] == [
        ("aws-core", "vendor", ["@aws-sdk/client-s3"])]


def test_stack_lists_official_plugins_named_after_a_dependency(mod: ModuleType) -> None:
    official = mod.OFFICIAL_MARKETPLACE
    data = catalog(plugin("typescript-lsp", marketplace=official), plugin("playwright", marketplace=official),
                   plugin("unrelated", marketplace=official))
    found = mod.find_stack_candidates(data, {"microsoft": ["typescript", "@playwright/test"]})
    assert sorted((c["name"], c["tier"], c["dependencies"][0]) for c in found) == [
        ("playwright", "official", "@playwright/test"), ("typescript-lsp", "official", "typescript")]


@pytest.mark.parametrize("name, dep", [
    ("invite-tools", "vite"),
    ("grafana-mcp", "mcp"),
    ("ui5-typescript-conversion", "typescript"),
])
def test_stack_compares_only_the_start_of_the_plugin_name(mod: ModuleType, name: str, dep: str) -> None:
    data = catalog(plugin(name, marketplace=mod.OFFICIAL_MARKETPLACE))
    assert mod.find_stack_candidates(data, {"owner": [dep]}) == []


def test_stack_ignores_other_products_of_a_big_vendor(mod: ModuleType) -> None:
    data = catalog(plugin("azure", "https://github.com/microsoft/azure", marketplace=mod.OFFICIAL_MARKETPLACE),
                   plugin("dataverse", "https://github.com/microsoft/dataverse"))
    assert mod.find_stack_candidates(data, {"microsoft": ["typescript", "@playwright/test"]}) == []


def test_stack_ignores_third_party_plugin_named_after_a_dependency(mod: ModuleType) -> None:
    data = catalog(plugin("express-helper", "https://github.com/someone/x"))
    assert mod.find_stack_candidates(data, {"expressjs": ["express"]}) == []


def test_stack_skips_installed_plugins(mod: ModuleType) -> None:
    data = catalog(plugin("aws-core", "https://github.com/aws/x"), installed=("aws-core@claude-plugins-official",))
    assert mod.find_stack_candidates(data, {"aws": ["a"]}) == []


def test_stack_is_ordered_by_installs_and_capped(mod: ModuleType) -> None:
    many = [plugin(f"typescript-{i}", marketplace=mod.OFFICIAL_MARKETPLACE, installs=i) for i in range(30)]
    found = mod.find_stack_candidates(catalog(*many), {"microsoft": ["typescript"]})
    assert found[0]["name"] == "typescript-29" and len(found) == mod.MAX_STACK_CANDIDATES


def test_cli_lists_the_stack_without_any_need(tmp_path: Path, mod: ModuleType) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"zod": "4"}}))
    write_package(tmp_path, "zod", "https://github.com/colinhacks/zod")
    data = catalog(plugin("zod-tools", marketplace=mod.OFFICIAL_MARKETPLACE))
    done = run_cli(["--repo", str(tmp_path)], json.dumps(data))
    assert done.returncode == 0, done.stderr
    report = json.loads(done.stdout)
    assert report["needs"] == []
    assert [c["name"] for c in report["stack_candidates"]] == ["zod-tools"]


def run_cli(args: list[str], stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS_DIR / "find_skill_candidates.py"), *args],
                          input=stdin, capture_output=True, text=True, timeout=30)


def test_cli_prints_json_report_without_network(tmp_path: Path, mod: ModuleType) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"missing": "1"}}))
    data = catalog(plugin("official-one", marketplace=mod.OFFICIAL_MARKETPLACE, description="mutation testing"))
    done = run_cli(["--repo", str(tmp_path), "--need", "mutation testing"], json.dumps(data))
    assert done.returncode == 0, done.stderr
    report = json.loads(done.stdout)
    assert [c["name"] for c in report["needs"][0]["candidates"]] == ["official-one"]
    assert report["needs"][0]["need"] == "mutation testing"
    assert report["vendors"] == {} and report["dependencies_without_vendor"] == 1
    assert report["package_skills"] == []


@pytest.mark.parametrize("need", ["", "   "])
def test_cli_rejects_a_blank_need(tmp_path: Path, need: str) -> None:
    done = run_cli(["--repo", str(tmp_path), "--need", need], json.dumps(catalog()))
    assert done.returncode == 2
    assert "--need" in done.stderr


@pytest.mark.parametrize("stdin", ["not json", "[]", "{}"])
def test_cli_rejects_a_bad_catalog(tmp_path: Path, stdin: str) -> None:
    done = run_cli(["--repo", str(tmp_path), "--need", "x"], stdin)
    assert done.returncode == 2
    assert "claude plugin list" in done.stderr
