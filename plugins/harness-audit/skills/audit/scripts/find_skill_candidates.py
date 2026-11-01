"""Candidates for ready-made skills and plugins that fit the person's needs and the project stack.

The catalog arrives on stdin: claude plugin list --json --available. Each --need is one query of 1-3
English words: the catalog must contain every word of the query, so a synonym is another --need. The
real vendor comes from the repository field of installed dependencies, not from a similar name.
stack_candidates need no query: official and vendor plugins named after a project dependency.

With --network the query goes to skills.sh and third-party repositories are checked through the GitHub
API. Without it third-party candidates stay in not_checked. The script narrows the list; the agent decides.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OFFICIAL_MARKETPLACE = "claude-plugins-official"
OFFICIAL_OWNER = "anthropics"
MIN_STARS = 3000
MAX_DAYS_SINCE_PUSH = 180
MAX_CANDIDATES_PER_NEED = 8
MAX_STACK_CANDIDATES = 15
MAX_GITHUB_LOOKUPS_PER_NEED = 8
MAX_GITHUB_LOOKUPS = 50
SKILLS_SH_RESULTS = 15
DESCRIPTION_LIMIT = 200
PACKAGE_SKILLS_LIMIT = 20
TIMEOUT_SECONDS = 15

SKILLS_SH_URL = "https://skills.sh/api/search?"
GITHUB_REPO_URL = "https://api.github.com/repos/"

TIER_ORDER = {"official": 0, "vendor": 1, "popular": 2}
VENV_DIRS = (".venv", "venv", "env")
SKIP_DIRS = {".git", ".claude", "node_modules", "__pycache__", "dist", "build", *VENV_DIRS}
PYTHON_MANIFESTS = ("pyproject.toml", "Pipfile", "setup.py", "setup.cfg", "requirements*.txt")
RATE_LIMIT_CODES = (403, 429)

_GITHUB_URL = re.compile(r"github\.com[/:]([\w-]+)/([\w.-]+)", re.IGNORECASE)
_SHORTHAND = re.compile(r"^(?:github:)?([\w-]+)/([\w.-]+)$")
_NON_REPO_OWNERS = {"sponsors"}

Fetch = Callable[[str], Any]


def github_repo(url: str) -> str | None:
    text = url.strip()
    match = _GITHUB_URL.search(text) or _SHORTHAND.match(text)
    if match is None or match[1].lower() in _NON_REPO_OWNERS:
        return None
    return f"{match[1]}/{match[2].removesuffix('.git')}"


def _owner(repo: str) -> str:
    return repo.split("/")[0].lower()


def _is_awesome_list(repo: str) -> bool:
    return "awesome" in repo.split("/")[-1].lower()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _project_dirs(repo: Path) -> Iterator[Path]:
    for root, dirs, _files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        yield Path(root)


def _site_packages(folder: Path) -> list[Path]:
    return [path for name in VENV_DIRS for path in (folder / name).glob("lib/python*/site-packages")]


def _installed_manifest(dep: str, start: Path, repo: Path) -> Path | None:
    folder = start
    while True:
        candidate = folder / "node_modules" / dep / "package.json"
        if candidate.is_file():
            return candidate
        if folder == repo or folder == folder.parent:
            return None
        folder = folder.parent


def _npm_repository(manifest: Path) -> str | None:
    value = _load_json(manifest).get("repository")
    url = value.get("url") if isinstance(value, dict) else value
    return github_repo(url) if isinstance(url, str) else None


def _npm_dependencies(folder: Path) -> list[str]:
    manifest = _load_json(folder / "package.json")
    deps: list[str] = []
    for section in ("dependencies", "devDependencies"):
        value = manifest.get(section)
        if isinstance(value, dict):
            deps += [dep for dep in value if not dep.startswith("@types/")]
    return deps


def _python_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _direct_python_names(folders: list[Path]) -> set[str] | None:
    """Words from Python manifests; None if there are none and direct dependencies cannot be known.

    Parsed without TOML: an extra word is harmless, and Python 3.10 has no tomllib.
    """
    texts: list[str] = []
    for folder in folders:
        for pattern in PYTHON_MANIFESTS:
            for path in folder.glob(pattern):
                try:
                    texts.append(path.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    continue
    if not texts:
        return None
    return {_python_name(word) for word in re.findall(r"[A-Za-z0-9][\w.-]*", " ".join(texts))}


def _python_packages(site_packages: Path) -> Iterator[tuple[str, str]]:
    for metadata in sorted(site_packages.glob("*.dist-info/METADATA")):
        name, repository = "", None
        try:
            lines = metadata.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line:
                break
            if line.startswith("Name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith(("Project-URL:", "Home-page:")) and repository is None:
                repository = github_repo(line) if "github.com" in line else None
        if name and repository:
            yield name, repository


def _go_requirements(go_mod: Path) -> Iterator[tuple[str, str]]:
    try:
        lines = go_mod.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        text = line.strip()
        match = _GITHUB_URL.search(text)
        if match and not text.startswith("module ") and "// indirect" not in text:
            yield match[0], f"{match[1]}/{match[2]}"


def find_vendors(repo: Path) -> tuple[dict[str, list[str]], int]:
    """Returns {lowercase GitHub organization: dependencies} and the number of unknown ones."""
    root = repo.resolve()
    vendors: dict[str, list[str]] = {}
    unknown = 0

    def add(dep: str, repository: str) -> None:
        deps = vendors.setdefault(_owner(repository), [])
        if dep not in deps:
            deps.append(dep)

    folders = list(_project_dirs(root))
    direct = _direct_python_names(folders)
    for folder in folders:
        for dep in _npm_dependencies(folder):
            manifest = _installed_manifest(dep, folder, root)
            repository = _npm_repository(manifest) if manifest else None
            if repository:
                add(dep, repository)
            else:
                unknown += 1
        for site_packages in _site_packages(folder):
            for name, repository in _python_packages(site_packages):
                if direct is None or _python_name(name) in direct:
                    add(name, repository)
        for dep, repository in _go_requirements(folder / "go.mod"):
            add(dep, repository)
    return vendors, unknown


def _frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    match = re.match(r"---\n(.*?)\n---", text, re.DOTALL)
    if match is None:
        return {}
    fields = re.findall(r"^(name|description):\s*(.+)$", match[1], re.MULTILINE)
    return {key: value.strip()[:DESCRIPTION_LIMIT] for key, value in fields}


def find_package_skills(repo: Path) -> list[dict[str, str]]:
    """Skills a vendor ships inside its own package."""
    root = repo.resolve()
    found: list[dict[str, str]] = []
    for folder in _project_dirs(root):
        for packages in [folder / "node_modules", *_site_packages(folder)]:
            for current, _dirs, files in os.walk(packages):
                if "SKILL.md" in files:
                    path = Path(current) / "SKILL.md"
                    meta = _frontmatter(path)
                    found.append({"path": path.relative_to(root).as_posix(), "name": meta.get("name", ""),
                                  "description": meta.get("description", "")})
    return sorted(found, key=lambda item: item["path"])[:PACKAGE_SKILLS_LIMIT]


def matches(query: str, text: str) -> bool:
    return all(re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", text, re.IGNORECASE)
               for word in query.split())


def _catalog_repo(source: Any) -> str | None:
    if not isinstance(source, dict):
        return None
    url = source.get("url") or source.get("repo")
    return github_repo(url) if isinstance(url, str) else None


def _shorten(text: Any) -> str:
    return text[:DESCRIPTION_LIMIT] if isinstance(text, str) else ""


def _catalog_entries(catalog: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    """Plugins that are not installed, without duplicates: the entry and its full search text."""
    installed = {str(item.get("id", "")).split("@")[0] for item in catalog.get("installed", [])}
    best: dict[str, tuple[dict[str, Any], str]] = {}
    for plugin in catalog.get("available", []):
        name = plugin.get("name", "")
        marketplace = plugin.get("marketplaceName")
        if name in installed or (name in best and marketplace != OFFICIAL_MARKETPLACE):
            continue
        description = plugin.get("description") or ""
        entry = {"name": name, "origin": "catalog", "plugin_id": plugin.get("pluginId"),
                 "repo": _catalog_repo(plugin.get("source")), "marketplace": marketplace,
                 "installs": plugin.get("installCount"), "description": _shorten(description)}
        best[name] = (entry, f"{name} {description}")
    return list(best.values())


def search_catalog(catalog: dict[str, Any], query: str) -> list[dict[str, Any]]:
    return [entry for entry, text in _catalog_entries(catalog) if matches(query, text)]


def _first_word(name: str) -> str:
    return name.lower().split("-")[0]


def _dependency_key(dep: str) -> str:
    name = dep[1:].split("/")[0] if dep.startswith("@") else dep.rsplit("/", 1)[-1]
    return _first_word(name)


def find_stack_candidates(catalog: dict[str, Any], vendors: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Official and vendor plugins whose name starts with the name of a project dependency.

    Only the start of the name is compared: "grafana-mcp" has nothing to do with the dependency "mcp".
    Belonging to a vendor is no reason by itself: Microsoft ships TypeScript, but Azure is unrelated to it.
    """
    by_key: dict[str, list[str]] = {}
    for deps in vendors.values():
        for dep in deps:
            by_key.setdefault(_dependency_key(dep), []).append(dep)
    found: list[dict[str, Any]] = []
    for entry, _text in _catalog_entries(catalog):
        tier = _trusted_tier(entry, vendors)
        deps = by_key.get(_first_word(entry["name"]))
        if tier is not None and deps:
            found.append({**entry, "tier": tier, "dependencies": deps[:3]})
    found.sort(key=lambda item: -(item.get("installs") or 0))
    return found[:MAX_STACK_CANDIDATES]


def search_skills_sh(query: str, fetch: Fetch) -> list[dict[str, Any]]:
    address = SKILLS_SH_URL + urllib.parse.urlencode({"q": query, "limit": SKILLS_SH_RESULTS})
    data = fetch(address)
    found: list[dict[str, Any]] = []
    for item in data.get("skills", []) if isinstance(data, dict) else []:
        source = item.get("source") if isinstance(item, dict) else None
        if isinstance(source, str) and isinstance(item.get("skillId"), str):
            installs = item.get("installs")
            found.append({"name": item["skillId"], "origin": "skills.sh", "repo": github_repo(source),
                          "marketplace": None, "installs": installs if isinstance(installs, int) else None,
                          "description": ""})
    return found


def _days_since_push(info: dict[str, Any], now: datetime) -> int | None:
    pushed_at = info.get("pushed_at")
    if not isinstance(pushed_at, str):
        return None
    try:
        return (now - datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))).days
    except ValueError:
        return None


def is_popular(info: dict[str, Any], now: datetime) -> bool:
    days = _days_since_push(info, now)
    return (info.get("stargazers_count", 0) >= MIN_STARS and days is not None
            and days <= MAX_DAYS_SINCE_PUSH and not info.get("archived", False))


def _trusted_tier(candidate: dict[str, Any], vendors: dict[str, list[str]]) -> str | None:
    repo = candidate.get("repo")
    owner = _owner(repo) if repo else None
    if candidate.get("marketplace") == OFFICIAL_MARKETPLACE or owner == OFFICIAL_OWNER:
        return "official"
    return "vendor" if owner in vendors else None


def classify(candidate: dict[str, Any], vendors: dict[str, list[str]], info: dict[str, Any] | None,
             now: datetime) -> str:
    trusted = _trusted_tier(candidate, vendors)
    if trusted is not None:
        return trusted
    repo = candidate.get("repo")
    if repo and _is_awesome_list(repo):
        return "other"
    if info is None:
        return "not_checked"
    return "popular" if is_popular(info, now) else "other"


def _sort_key(candidate: dict[str, Any]) -> tuple[int, int]:
    return TIER_ORDER[candidate["tier"]], -(candidate.get("installs") or 0)


class _GitHub:
    """Repository checks for one run: cache, request limits, stop on rate limit.

    Without a login GitHub allows 60 requests an hour. The share per need keeps early queries from eating it all.
    """

    def __init__(self, fetch: Fetch | None, errors: list[str]) -> None:
        self.fetch, self.errors = fetch, errors
        self.cache: dict[str, dict[str, Any] | None] = {}
        self.blocked = fetch is None
        self.share_left = MAX_GITHUB_LOOKUPS_PER_NEED

    def start_need(self) -> None:
        self.share_left = MAX_GITHUB_LOOKUPS_PER_NEED

    def info(self, repo: str) -> dict[str, Any] | None:
        key = repo.lower()
        if key in self.cache:
            return self.cache[key]
        if self.blocked or self.share_left <= 0 or len(self.cache) >= MAX_GITHUB_LOOKUPS:
            return None
        self.share_left -= 1
        self.cache[key] = self._request(repo)
        return self.cache[key]

    def _request(self, repo: str) -> dict[str, Any] | None:
        assert self.fetch is not None
        try:
            data = self.fetch(GITHUB_REPO_URL + repo)
        except urllib.error.HTTPError as error:
            if error.code in RATE_LIMIT_CODES:
                self.blocked = True
            self.errors.append(f"GitHub {repo}: HTTP {error.code}")
            return None
        except (OSError, ValueError) as error:
            self.errors.append(f"GitHub {repo}: {error}")
            return None
        return data if isinstance(data, dict) else None


def _with_tier(candidate: dict[str, Any], vendors: dict[str, list[str]], github: _GitHub,
               now: datetime) -> dict[str, Any]:
    tier = classify(candidate, vendors, None, now)
    info = None
    if tier == "not_checked" and candidate.get("repo"):
        info = github.info(candidate["repo"])
        tier = classify(candidate, vendors, info, now)
    result = {**candidate, "tier": tier}
    if tier == "popular" and info is not None:
        result |= {"stars": info.get("stargazers_count"), "days_since_push": _days_since_push(info, now),
                   "license": (info.get("license") or {}).get("spdx_id")}
    return result


def _search_need(need: str, catalog: dict[str, Any], vendors: dict[str, list[str]], now: datetime,
                 fetch: Fetch | None, github: _GitHub, errors: list[str]) -> dict[str, Any]:
    github.start_need()
    found = search_catalog(catalog, need)
    if fetch is not None:
        try:
            found += search_skills_sh(need, fetch)
        except (OSError, ValueError) as error:
            errors.append(f"skills.sh «{need}»: {error}")
    found.sort(key=lambda item: -(item.get("installs") or 0))
    tiered = [_with_tier(candidate, vendors, github, now) for candidate in found]
    shown = sorted((item for item in tiered if item["tier"] in TIER_ORDER), key=_sort_key)
    return {"need": need, "candidates": shown[:MAX_CANDIDATES_PER_NEED],
            "not_checked": [item["name"] for item in tiered if item["tier"] == "not_checked"],
            "dropped": sum(1 for item in tiered if item["tier"] == "other")}


def collect(catalog: dict[str, Any], vendors: dict[str, list[str]], needs: list[str], now: datetime,
            fetch: Fetch | None = None) -> dict[str, Any]:
    errors: list[str] = []
    github = _GitHub(fetch, errors)
    results = [_search_need(need, catalog, vendors, now, fetch, github, errors) for need in needs]
    return {"needs": results, "errors": errors}


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "harness-audit", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except http.client.HTTPException as error:
        raise OSError(f"truncated response: {error!r}") from error


def _read_catalog() -> dict[str, Any] | None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return None
    return data if isinstance(data, dict) and "available" in data else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--need", action="append", default=[])
    parser.add_argument("--network", action="store_true")
    args = parser.parse_args()
    needs = [need.strip() for need in args.need if need.strip()]
    if args.need and not needs:
        print("--need must not be empty", file=sys.stderr)
        return 2
    catalog = _read_catalog()
    if catalog is None:
        print("Expected the output of claude plugin list --json --available on stdin", file=sys.stderr)
        return 2
    repo = Path(args.repo)
    vendors, unknown = find_vendors(repo)
    result = collect(catalog, vendors, needs, datetime.now(timezone.utc), fetch_json if args.network else None)
    report = {"vendors": vendors, "dependencies_without_vendor": unknown,
              "package_skills": find_package_skills(repo),
              "stack_candidates": find_stack_candidates(catalog, vendors), **result}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
