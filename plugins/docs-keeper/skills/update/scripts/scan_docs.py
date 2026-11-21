"""Facts about a repository's documentation, for the docs-keeper skills.

impact  Which documents a code change touches. Picks the change (a base ref, the branch
        against the default branch, uncommitted work, or the last commit), then reports
        names that left the code and files that were removed or renamed, each with the
        documents that still mention them, and new flags, settings and routes that no
        document mentions.

links   Broken relative links, heading anchors and backticked paths in documents, and with
        --orphans the documents under docs/ that nothing points to.

Both print JSON. Documents are .md, .mdx, .rst and .adoc files that git does not ignore.
Each document has a kind: living, instructions, generated, decision, changelog or archive.
The script reads names, not meaning: a document whose names all still exist but whose
described behaviour changed is not reported.
"""

import argparse
import fnmatch
import json
import posixpath
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote


class DocumentKind(str, Enum):
    LIVING = "living"
    INSTRUCTIONS = "instructions"
    GENERATED = "generated"
    DECISION = "decision"
    CHANGELOG = "changelog"
    ARCHIVE = "archive"


EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
DOCUMENT_SUFFIXES = (".md", ".mdx", ".rst", ".adoc")
MARKDOWN_SUFFIXES = (".md", ".mdx")
DOCS_ROOTS = {"docs", "doc", "documentation"}
INSTRUCTION_NAMES = {"claude.md", "claude.local.md", "agents.md", "gemini.md", "copilot-instructions.md"}
INSTRUCTION_FOLDERS = (".claude/rules/", ".cursor/rules/", ".github/instructions/")
ARCHIVE_FOLDERS = {"archive", "archived", "attic", "superseded", "obsolete", "deprecated"}
DECISION_FOLDERS = {"decisions", "adr", "adrs", "architecture-decisions", "rfc", "rfcs"}
DECISION_INDEX_NAMES = {"readme.md", "index.md", "template.md"}
GENERATED_FOLDERS = {"generated", "_generated", "autogen"}
CHANGELOG_STEMS = {"changelog", "release-notes", "release_notes"}
GENERIC_CHANGELOG_STEMS = {"history", "releases", "news", "changes"}
NAVIGATION_FILES = ("mkdocs.yml", "mkdocs.yaml", "sidebars.js", "sidebars.ts", "docs.json", "mint.json",
                    "_toc.yml", "_sidebar.md")
GENERATED_MARKER_RE = re.compile(
    r"do not edit|auto-?generated|generated (?:by|from|with)|this file is generated", re.IGNORECASE)

VERSION_HEADING_RE = re.compile(r"^\s{0,3}(?:#{1,6}\s+)?\[?(?:v?\d+\.\d+|unreleased\b)",
                                re.IGNORECASE | re.MULTILINE)
IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{3,}")
FLAG_RE = re.compile(r"(?<![\w-])--[a-z0-9][a-z0-9-]+")
QUOTED_FLAG_RE = re.compile(r"""["'](--[a-z0-9][a-z0-9-]+)["']""")
ROUTE_RE = re.compile(r"""["'`](/[A-Za-z0-9_{}:.\-/]{3,})["'`]""")
ROUTE_CONTEXT_RE = re.compile(r"route|router|\b(?:get|post|put|patch|delete)\b|path\(|@app\.|@api\.", re.IGNORECASE)
SETTING_RE = re.compile(r"""(?:["'`]|(?i:env\.)|\$\{?)([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b""")
ENVIRONMENT_FILE_SETTING_RE = re.compile(r"^(?:export\s+)?([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)=")
ENVIRONMENT_RE = re.compile(r"environ|getenv|process\.env|\benv\b|ENV\[|import\.meta\.env", re.IGNORECASE)
CAMEL_HUMP_RE = re.compile(r"[a-z0-9][A-Z]")

FENCE_RE = re.compile(r"^\s{0,3}(```|~~~)")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
LINK_RE = re.compile(r"!?\[(?:[^\[\]]|\[[^\[\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'(][^)]*)?\)")
REFERENCE_RE = re.compile(r"^\s{0,3}\[(?!\^)[^\]]+\]:\s*<?([^\s>]+)>?")
IMPORT_RE = re.compile(r"(?<![\w`])@((?:\.{1,2}/|[\w-])[^\s`]*)")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
SETEXT_UNDERLINE_RE = re.compile(r"^\s{0,3}(=+|-+)\s*$")
EXPLICIT_ANCHOR_RE = re.compile(r"""(?:\bid|\bname)=["']([^"']+)["']|\{#([^}\s]+)\}""")
MARKDOWN_LINK_TEXT_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
LINE_SUFFIX_RE = re.compile(r":\d+(?::\d+)?$")
PATH_SKIP_MARKERS = ("://", "*", "<", ">", "{", "}", "$", " ", "|", "=", "\\")
PATH_SUFFIXES = (".md", ".mdx", ".rst", ".json", ".yml", ".yaml", ".toml", ".py", ".ts", ".tsx", ".js", ".jsx",
                 ".sh", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".sql", ".html", ".css", ".txt",
                 ".cfg", ".ini", ".tf")
HISTORY_KINDS = {DocumentKind.DECISION, DocumentKind.CHANGELOG, DocumentKind.ARCHIVE}
INDEX_NAMES = {"readme.md", "index.md", "claude.md", "agents.md"}
TEST_PATH_GLOBS = ("**/tests/**", "**/test/**", "**/__tests__/**", "**/test_*", "**/*_test.*",
                   "**/*.test.*", "**/*.spec.*")
NAMES_PER_GREP = 400
HEAD_LINES = 20
MAX_LISTED_DOCUMENTS = 60
MAX_TEXT_FILE_BYTES = 1_000_000
MAX_MENTION_TEXT = 160


@dataclass
class Document:
    path: str
    kind: DocumentKind
    lines: list[str]


@dataclass
class ChangedFile:
    status: str
    path: str
    old_path: str = ""


@dataclass
class Scope:
    base_commit: str
    description: str


def run_git(repo: Path, *arguments: str) -> tuple[bool, str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), "-c", "core.quotepath=off", *arguments],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    return completed.returncode == 0, completed.stdout


def read_git(repo: Path, *arguments: str) -> str:
    succeeded, output = run_git(repo, *arguments)
    return output if succeeded else ""


def find_repository_root(start: str) -> Path | None:
    succeeded, output = run_git(Path(start), "rev-parse", "--show-toplevel")
    return Path(output.strip()) if succeeded and output.strip() else None


def list_files(repo: Path) -> list[str]:
    listed = read_git(repo, "ls-files", "-co", "--exclude-standard", "-z").split("\0")
    return sorted({path for path in listed if path and (repo / path).is_file()})


def read_text(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_TEXT_FILE_BYTES:
            return ""
        content = path.read_bytes()
    except OSError:
        return ""
    return "" if b"\0" in content else content.decode("utf-8", errors="replace")


def is_document(path: str) -> bool:
    return path.lower().endswith(DOCUMENT_SUFFIXES)


def classify_document(path: str, head: str) -> DocumentKind:
    pure = PurePosixPath(path)
    folders = {part.lower() for part in pure.parts[:-1]}
    name = pure.name.lower()
    stem = pure.stem.lower()
    if folders & ARCHIVE_FOLDERS:
        return DocumentKind.ARCHIVE
    if stem in CHANGELOG_STEMS or stem.startswith("changelog") or (
            stem in GENERIC_CHANGELOG_STEMS and VERSION_HEADING_RE.search(head)):
        return DocumentKind.CHANGELOG
    if folders & DECISION_FOLDERS and name not in DECISION_INDEX_NAMES:
        return DocumentKind.DECISION
    if name in INSTRUCTION_NAMES or any(folder in f"/{path.lower()}" for folder in INSTRUCTION_FOLDERS):
        return DocumentKind.INSTRUCTIONS
    if folders & GENERATED_FOLDERS or GENERATED_MARKER_RE.search(head.partition("\n")[0]):
        return DocumentKind.GENERATED
    return DocumentKind.LIVING


def load_documents(repo: Path, files: list[str]) -> list[Document]:
    documents = []
    for path in files:
        if is_document(path):
            lines = read_text(repo / path).splitlines()
            documents.append(Document(path, classify_document(path, "\n".join(lines[:HEAD_LINES])), lines))
    return documents


def find_default_branch(repo: Path) -> str:
    remote_head = read_git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
    for candidate in (remote_head, "origin/main", "origin/master", "main", "master"):
        if candidate and run_git(repo, "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}")[0]:
            return candidate
    return ""


def pick_scope(repo: Path, requested_base: str) -> Scope:
    head = read_git(repo, "rev-parse", "--verify", "--quiet", "HEAD").strip()
    if not head:
        return Scope(EMPTY_TREE, "every file: the repository has no commits yet")
    if requested_base:
        merge_base = read_git(repo, "merge-base", requested_base, "HEAD").strip() or requested_base
        return Scope(merge_base, f"changes since {requested_base}, uncommitted work included")
    default_branch = find_default_branch(repo)
    current_branch = read_git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if default_branch and current_branch not in (default_branch, default_branch.removeprefix("origin/")):
        merge_base = read_git(repo, "merge-base", default_branch, "HEAD").strip()
        if merge_base and merge_base != head:
            return Scope(merge_base, f"branch {current_branch} since {default_branch}, uncommitted work included")
    if read_git(repo, "status", "--porcelain").strip():
        return Scope("HEAD", "uncommitted changes")
    if run_git(repo, "rev-parse", "--verify", "--quiet", "HEAD~1")[0]:
        return Scope("HEAD~1", "the last commit: the working tree is clean")
    return Scope(EMPTY_TREE, "every file: the repository has a single commit")


def list_changed_files(repo: Path, base_commit: str) -> list[ChangedFile]:
    fields = read_git(repo, "diff", "--name-status", "-M", "-z", base_commit).split("\0")
    changed: list[ChangedFile] = []
    position = 0
    while position + 1 < len(fields) and fields[position]:
        status = fields[position][0]
        if status in "RC" and position + 2 < len(fields):
            changed.append(ChangedFile(status, fields[position + 2], fields[position + 1]))
            position += 3
        else:
            changed.append(ChangedFile(status, fields[position + 1]))
            position += 2
    known_paths = {file.path for file in changed}
    for path in read_git(repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0"):
        if path and path not in known_paths:
            changed.append(ChangedFile("A", path))
    return changed


def strip_diff_prefix(header_path: str) -> str:
    path = header_path.strip().strip('"')
    return "" if path == "/dev/null" else path[2:] if path[:2] in ("a/", "b/") else path


def read_changed_code_lines(repo: Path, base_commit: str,
                            changed: list[ChangedFile]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    removed: list[tuple[str, str]] = []
    added: list[tuple[str, str]] = []
    path = ""
    is_inside_hunk = False
    diff = read_git(repo, "diff", "-M", "-U0", "--no-color", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/",
                    base_commit)
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            path, is_inside_hunk = "", False
        elif not is_inside_hunk and line.startswith(("--- ", "+++ ")):
            path = strip_diff_prefix(line[4:]) or path
        elif line.startswith("@@"):
            is_inside_hunk = True
        elif is_inside_hunk and path and not is_document(path):
            if line.startswith("-"):
                removed.append((path, line[1:]))
            elif line.startswith("+"):
                added.append((path, line[1:]))
    tracked = set(read_git(repo, "ls-files", "-z").split("\0"))
    for file in changed:
        if file.status == "A" and file.path not in tracked and not is_document(file.path):
            added.extend((file.path, line) for line in read_text(repo / file.path).splitlines())
    return removed, added


def is_distinctive_identifier(identifier: str) -> bool:
    core = identifier.strip("_")
    return "_" in core or bool(CAMEL_HUMP_RE.search(core))


def extract_names(line: str) -> set[str]:
    names = {name for name in IDENTIFIER_RE.findall(line) if is_distinctive_identifier(name)}
    names.update(FLAG_RE.findall(line))
    names.update(ROUTE_RE.findall(line))
    return names


def is_test_path(path: str) -> bool:
    return any(fnmatch.fnmatchcase(f"/{path}", test_glob) for test_glob in TEST_PATH_GLOBS)


def find_names_in_code(repo: Path, names: set[str], tree: str = "", include_tests: bool = False) -> set[str]:
    if not names:
        return set()
    arguments = ["grep", "--no-color", "-h", "-I", "-F"] + ([] if tree else ["--untracked"])
    for name in sorted(names):
        arguments += ["-e", name]
    if tree:
        arguments.append(tree)
    arguments += ["--", ".", *[f":(exclude)*{suffix}" for suffix in DOCUMENT_SUFFIXES]]
    if not include_tests:
        arguments += [f":(exclude,glob){test_glob}" for test_glob in TEST_PATH_GLOBS]
    route_patterns = {name: build_name_pattern(name) for name in names if name.startswith("/")}
    present: set[str] = set()
    for line in read_git(repo, *arguments).splitlines():
        present |= extract_names(line) & names
        present |= {route for route, pattern in route_patterns.items() if pattern.search(line)}
    return present


def find_names_in_code_in_batches(repo: Path, names: set[str], include_tests: bool = False) -> set[str]:
    ordered = sorted(names)
    present: set[str] = set()
    for start in range(0, len(ordered), NAMES_PER_GREP):
        present |= find_names_in_code(repo, set(ordered[start:start + NAMES_PER_GREP]), include_tests=include_tests)
    return present


def build_name_pattern(name: str) -> re.Pattern[str]:
    escaped = re.escape(name)
    if name.startswith("--"):
        return re.compile(rf"(?<![\w-]){escaped}(?![\w-])")
    if name.startswith("/"):
        return re.compile(rf"(?<![\w/.-]){escaped}(?![\w/-])")
    return re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])")


def build_path_patterns(path: str, current_basenames: set[str]) -> list[re.Pattern[str]]:
    pure = PurePosixPath(path)
    needles = [path]
    if len(pure.parts) > 2:
        needles.append("/".join(pure.parts[-2:]))
    patterns = [re.compile(rf"(?<![A-Za-z0-9_-]){re.escape(needle)}(?![\w-])") for needle in needles]
    if pure.suffix and len(pure.stem) >= 4 and pure.name not in current_basenames:
        patterns.append(re.compile(rf"(?<![A-Za-z0-9_./-]){re.escape(pure.name)}(?![\w-])"))
    return patterns


def find_mentions(documents: list[Document], patterns: list[re.Pattern[str]], needle: str) -> list[dict[str, Any]]:
    mentions = []
    for document in documents:
        for line_number, line in enumerate(document.lines, start=1):
            if needle in line and any(pattern.search(line) for pattern in patterns):
                mentions.append({"file": document.path, "line": line_number, "kind": document.kind,
                                 "text": line.strip()[:MAX_MENTION_TEXT]})
    return mentions


def find_stale_names(repo: Path, removed: list[tuple[str, str]], documents: list[Document]) -> list[dict[str, Any]]:
    document_text = "\n".join(line for document in documents for line in document.lines)
    from_code = {name for path, line in removed if not is_test_path(path)
                 for name in extract_names(line) if name in document_text}
    from_tests = {name for path, line in removed if is_test_path(path)
                  for name in extract_names(line) if name in document_text} - from_code
    present = (find_names_in_code_in_batches(repo, from_code)
               | find_names_in_code_in_batches(repo, from_tests, include_tests=True))
    stale = []
    for name in sorted((from_code | from_tests) - present):
        mentions = find_mentions(documents, [build_name_pattern(name)], name)
        if mentions:
            stale.append({"name": name, "reason": "name no longer in the code outside tests", "mentions": mentions})
    return stale


def find_stale_paths(changed: list[ChangedFile], files: list[str], documents: list[Document]) -> list[dict[str, Any]]:
    current_basenames = {PurePosixPath(path).name for path in files}
    stale = []
    for file in changed:
        if file.status == "D":
            old_path, reason = file.path, "file removed"
        elif file.status == "R":
            old_path, reason = file.old_path, f"file renamed to {file.path}"
        else:
            continue
        mentions = find_mentions(documents, build_path_patterns(old_path, current_basenames),
                                 PurePosixPath(old_path).name)
        if mentions:
            stale.append({"name": old_path, "reason": reason, "mentions": mentions})
    return stale


def collect_added_names(added: list[tuple[str, str]]) -> dict[str, tuple[str, str]]:
    names: dict[str, tuple[str, str]] = {}
    for path, line in added:
        for flag in QUOTED_FLAG_RE.findall(line):
            names.setdefault(flag, ("flag", path))
        if PurePosixPath(path).name.startswith(".env"):
            for setting in ENVIRONMENT_FILE_SETTING_RE.findall(line):
                names.setdefault(setting, ("setting", path))
        elif ENVIRONMENT_RE.search(line):
            for setting in SETTING_RE.findall(line):
                names.setdefault(setting, ("setting", path))
        if ROUTE_CONTEXT_RE.search(line):
            for route in ROUTE_RE.findall(line):
                names.setdefault(route, ("route", path))
    return names


def find_added_names_without_documents(repo: Path, base_commit: str, removed: list[tuple[str, str]],
                                       added: list[tuple[str, str]],
                                       documents: list[Document]) -> list[dict[str, str]]:
    names = collect_added_names(added)
    removed_names = {name for _, line in removed for name in extract_names(line)}
    new_names = {name for name in names if name not in removed_names}
    if base_commit != EMPTY_TREE:
        new_names -= find_names_in_code(repo, new_names, tree=base_commit)
    return [{"name": name, "kind": names[name][0], "file": names[name][1]} for name in sorted(new_names)
            if not find_mentions(documents, [build_name_pattern(name)], name)]


def describe_changed_file(file: ChangedFile) -> dict[str, str]:
    described = {"status": file.status, "path": file.path}
    if file.old_path:
        described["old_path"] = file.old_path
    return described


def group_documents_by_kind(documents: list[Document]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for document in documents:
        grouped.setdefault(document.kind, []).append(document.path)
    return {kind: paths[:MAX_LISTED_DOCUMENTS] for kind, paths in sorted(grouped.items())}


def build_impact_report(repo: Path, requested_base: str) -> dict[str, Any]:
    scope = pick_scope(repo, requested_base)
    changed = list_changed_files(repo, scope.base_commit)
    files = list_files(repo)
    documents = load_documents(repo, files)
    removed, added = read_changed_code_lines(repo, scope.base_commit, changed)
    return {
        "scope": scope.description,
        "base_commit": scope.base_commit,
        "changed_code": [describe_changed_file(file) for file in changed if not is_document(file.path)],
        "changed_documents": [describe_changed_file(file) for file in changed if is_document(file.path)],
        "stale_mentions": find_stale_paths(changed, files, documents) + find_stale_names(repo, removed, documents),
        "added_names_without_documents": find_added_names_without_documents(
            repo, scope.base_commit, removed, added, documents),
        "document_count": len(documents),
        "documents": group_documents_by_kind(documents),
    }


def build_heading_slugs(heading: str) -> set[str]:
    text = HTML_TAG_RE.sub("", MARKDOWN_LINK_TEXT_RE.sub(r"\1", heading)).replace("`", "").replace("*", "")
    slugs = set()
    for variant in (text, re.sub(r"(?<!\w)_|_(?!\w)", "", text)):
        slugs.add(re.sub(r"[^\w\- ]", "", variant.strip().lower()).replace(" ", "-"))
    return slugs


def collect_anchors(lines: list[str]) -> set[str]:
    anchors: set[str] = set()
    seen_counts: dict[str, int] = {}
    is_inside_fence = False
    previous_line = ""
    for line in lines:
        if FENCE_RE.match(line):
            is_inside_fence = not is_inside_fence
            previous_line = ""
            continue
        if is_inside_fence:
            continue
        for match in EXPLICIT_ANCHOR_RE.finditer(line):
            anchors.add((match.group(1) or match.group(2)).lower())
        heading = HEADING_RE.match(line)
        heading_text = heading.group(1) if heading else ""
        if not heading and previous_line.strip() and SETEXT_UNDERLINE_RE.match(line):
            heading_text = previous_line.strip()
        for slug in build_heading_slugs(heading_text) if heading_text else ():
            count = seen_counts.get(slug, 0)
            seen_counts[slug] = count + 1
            anchors.add(slug if count == 0 else f"{slug}-{count}")
        previous_line = line
    return anchors


def list_prose_lines(lines: list[str]) -> list[tuple[int, str]]:
    prose = []
    is_inside_fence = False
    for line_number, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            is_inside_fence = not is_inside_fence
        elif not is_inside_fence:
            prose.append((line_number, line))
    return prose


def list_link_targets(line: str) -> list[str]:
    without_code = INLINE_CODE_RE.sub(" ", line)
    return LINK_RE.findall(without_code) + REFERENCE_RE.findall(without_code)


def resolve_link_path(document_path: str, target_path: str) -> str:
    decoded = unquote(target_path)
    if decoded.startswith("/"):
        return posixpath.normpath(decoded.lstrip("/"))
    return posixpath.normpath(posixpath.join(posixpath.dirname(document_path), decoded))


def clean_backticked_path(token: str) -> str:
    return LINE_SUFFIX_RE.sub("", token.strip().split("#", 1)[0]).rstrip(".,;:)")


def is_path_candidate(token: str) -> bool:
    return ("/" in token and not any(marker in token for marker in PATH_SKIP_MARKERS)
            and not token.startswith(("~", "/", "-", "@", ".git/")))


def build_path_index(files: list[str]) -> set[str]:
    index: set[str] = set()
    for path in files:
        parts = PurePosixPath(path).parts
        for end in range(1, len(parts) + 1):
            index.update("/".join(parts[start:end]) for start in range(end))
        stem_parts = (*parts[:-1], PurePosixPath(path).stem)
        index.update("/".join(stem_parts[start:]) for start in range(len(stem_parts)))
    return index


def is_ignored_by_git(repo: Path, path: str) -> bool:
    return run_git(repo, "check-ignore", "-q", "--", path)[0]


def check_backticked_path(repo: Path, document: Document, token: str, path_index: set[str],
                          top_level_names: set[str]) -> str:
    if not is_path_candidate(token):
        return ""
    cleaned = clean_backticked_path(token)
    normalized = "/".join(part for part in cleaned.strip("/").split("/") if part not in (".", "..", ""))
    if "/" not in cleaned or not normalized or normalized in path_index:
        return ""
    if (repo / cleaned).exists() or (repo / posixpath.dirname(document.path) / cleaned).exists():
        return ""
    if not normalized.endswith(PATH_SUFFIXES) and normalized.split("/", 1)[0] not in top_level_names:
        return ""
    return "" if is_ignored_by_git(repo, cleaned) else cleaned


def check_document_links(repo: Path, document: Document, anchors_by_path: dict[str, set[str]],
                         path_index: set[str], top_level_names: set[str]) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []

    def report(line_number: int, kind: str, target: str) -> None:
        problem = {"file": document.path, "line": line_number, "kind": kind, "target": target}
        if problem not in problems:
            problems.append(problem)

    for line_number, line in list_prose_lines(document.lines):
        for target in list_link_targets(line):
            if SCHEME_RE.match(target) or target.startswith("//") or "{" in target:
                continue
            target_path, _, anchor = target.partition("#")
            resolved = resolve_link_path(document.path, target_path) if target_path else document.path
            if not (repo / resolved).exists():
                report(line_number, "broken_link", target)
            elif anchor and resolved.lower().endswith(MARKDOWN_SUFFIXES):
                if resolved not in anchors_by_path:
                    anchors_by_path[resolved] = collect_anchors(read_text(repo / resolved).splitlines())
                if unquote(anchor).lower() not in anchors_by_path[resolved]:
                    report(line_number, "broken_anchor", target)
        if document.kind in HISTORY_KINDS:
            continue
        for token in INLINE_CODE_RE.findall(line):
            missing_path = check_backticked_path(repo, document, token, path_index, top_level_names)
            if missing_path:
                report(line_number, "missing_path", missing_path)
    return problems


def list_referenced_paths(repo: Path, documents: list[Document]) -> set[tuple[str, str]]:
    referenced: set[tuple[str, str]] = set()
    for document in documents:
        folder = posixpath.dirname(document.path)
        for _, line in list_prose_lines(document.lines):
            candidates = [target.partition("#")[0] for target in list_link_targets(line)
                          if not SCHEME_RE.match(target)]
            candidates += [clean_backticked_path(token) for token in INLINE_CODE_RE.findall(line)
                           if is_path_candidate(token)]
            candidates += IMPORT_RE.findall(INLINE_CODE_RE.sub(" ", line))
            for candidate in candidates:
                if not candidate:
                    continue
                decoded = unquote(candidate)
                for resolved in (posixpath.normpath(decoded.lstrip("/")),
                                 posixpath.normpath(posixpath.join(folder, decoded))):
                    if (repo / resolved).exists():
                        referenced.add((document.path, resolved))
    return referenced


def find_orphans(repo: Path, documents: list[Document]) -> list[dict[str, Any]]:
    references = list_referenced_paths(repo, documents)
    navigation_text = "".join(read_text(repo / folder / name)
                              for folder in ("", *sorted(DOCS_ROOTS)) for name in NAVIGATION_FILES)
    orphans = []
    for document in documents:
        parts = PurePosixPath(document.path).parts
        if len(parts) < 2 or parts[0].lower() not in DOCS_ROOTS or document.kind == DocumentKind.ARCHIVE:
            continue
        parent = posixpath.dirname(document.path)
        covering_paths = {document.path} | ({parent} if len(parts) > 2 else set())
        is_referenced = any(source != document.path and PurePosixPath(source).name.lower() in INDEX_NAMES
                            and target in covering_paths for source, target in references)
        inside_docs = "/".join(parts[1:])
        without_suffix = str(PurePosixPath(inside_docs).with_suffix(""))
        is_in_navigation = inside_docs in navigation_text or without_suffix in navigation_text
        if not is_referenced and not (navigation_text and is_in_navigation):
            orphans.append({"file": document.path, "line": 0, "kind": "orphan", "target": ""})
    return orphans


def build_links_report(repo: Path, requested_files: list[str], should_find_orphans: bool) -> list[dict[str, Any]]:
    files = list_files(repo)
    documents = load_documents(repo, files)
    requested = {posixpath.normpath(path) for path in requested_files}
    document_paths = {document.path for document in documents}
    path_index = build_path_index(files)
    top_level_names = {PurePosixPath(path).parts[0] for path in files if "/" in path}
    anchors_by_path: dict[str, set[str]] = {}
    problems: list[dict[str, Any]] = [{"file": path, "line": 0, "kind": "not_a_document", "target": ""}
                                      for path in sorted(requested - document_paths)]
    for document in documents:
        if not requested or document.path in requested:
            problems += check_document_links(repo, document, anchors_by_path, path_index, top_level_names)
    if should_find_orphans:
        problems += find_orphans(repo, documents)
    return problems


def make_repository_relative(repo: Path, file_argument: str) -> str:
    if not Path(file_argument).is_absolute() and (repo / file_argument).exists():
        return posixpath.normpath(Path(file_argument).as_posix())
    absolute = Path(file_argument).resolve()
    try:
        return absolute.relative_to(repo.resolve()).as_posix()
    except ValueError:
        return file_argument


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)
    impact_parser = subparsers.add_parser("impact")
    impact_parser.add_argument("--repo", default=".")
    impact_parser.add_argument("--base", default="")
    links_parser = subparsers.add_parser("links")
    links_parser.add_argument("--repo", default=".")
    links_parser.add_argument("--orphans", action="store_true")
    links_parser.add_argument("files", nargs="*")
    arguments = parser.parse_args()
    repo = find_repository_root(arguments.repo)
    if repo is None:
        print(json.dumps({"error": "not a git repository"}))
        return 2
    if arguments.command == "impact":
        if arguments.base and not run_git(repo, "rev-parse", "--verify", "--quiet", f"{arguments.base}^{{tree}}")[0]:
            print(json.dumps({"error": f"unknown base: {arguments.base}"}))
            return 2
        report: Any = build_impact_report(repo, arguments.base)
    else:
        files = [make_repository_relative(repo, file_argument) for file_argument in arguments.files]
        report = build_links_report(repo, files, arguments.orphans)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
