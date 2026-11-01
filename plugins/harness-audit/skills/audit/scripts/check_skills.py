"""Mechanical checks of skills: frontmatter, name, description, size, links, tables of contents, script paths.

The checks come from Anthropic's skill authoring guide and the Claude Code skills page.
The script only reads files. The "when to use" and third-person checks do not apply to skills
with `disable-model-invocation: true`: their description never reaches the model's context.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

NAME_RE = re.compile(r"[a-z0-9-]{1,64}")
# Russian alternatives stay on purpose: the audit also reads skills written in Russian.
WHEN_RE = re.compile(r"when|trigger|\buse\b|когда|использ|применя|если|триггер|просьб|просит", re.I)
PERSON_RE = re.compile(r"\b(I can|I will|You can)\b|(я помогу|я могу|ты можешь|вы можете)", re.I)
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
TOC_RE = re.compile(r"^#+\s*(Contents|Содержание|Оглавление)", re.M | re.I)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
BLOCK_SCALAR_RE = re.compile(r"[|>][+-]?\d*[+-]?")
SKILL_DIR_VAR = "${CLAUDE_SKILL_DIR}/"
MAX_DESCRIPTION = 1024
MAX_DESCRIPTION_WITH_WHEN = 1536
MAX_BODY_LINES = 500
TOC_FILE_LINES = 100
TOC_SEARCH_LINES = 40
AUDIT_SKILL_PREFIX = "harness-audit"  # the audit and its versions are not audited


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _frontmatter(text: str) -> tuple[dict[str, str] | None, str]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            break
    else:
        return None, text
    fields: dict[str, str] = {}
    key: str | None = None
    for line in lines[1:end]:
        match = re.match(r"^([\w-]+):[ \t]*(.*)$", line)
        if match:
            key = match.group(1)
            value = match.group(2).strip()
            # YAML block scalars (`>-`, `|`, `>2+`): the indicator itself is not part of the value
            fields[key] = "" if BLOCK_SCALAR_RE.fullmatch(value) else value
        elif key and line.startswith((" ", "\t")):
            fields[key] += " " + line.strip()
    cleaned = {k: re.sub(r"\s+", " ", v).strip().strip("\"'") for k, v in fields.items()}
    return cleaned, "\n".join(lines[end + 1:])


def _count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _issue(issue_id: str, file: str, message: str) -> dict[str, str]:
    return {"id": issue_id, "file": file, "message": message}


def _code_spans(text: str) -> list[str]:
    spans: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            spans.append(line)
        else:
            spans.extend(INLINE_CODE_RE.findall(line))
    return spans


def _check_description(fm: dict[str, str], manual: bool) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    description = fm["description"]
    full = (description + " " + fm.get("when_to_use", "")).strip()
    if not description:
        return [_issue("SK-03", "SKILL.md", "empty description")]
    if len(description) > MAX_DESCRIPTION:
        issues.append(_issue("SK-03", "SKILL.md", f"description is {len(description)} characters > {MAX_DESCRIPTION}"))
    if len(full) > MAX_DESCRIPTION_WITH_WHEN:
        issues.append(_issue("SK-03", "SKILL.md",
                             f"description + when_to_use is {len(full)} characters > {MAX_DESCRIPTION_WITH_WHEN}"))
    if "<" in description or ">" in description:
        issues.append(_issue("SK-03", "SKILL.md", "< or > characters in description"))
    if not manual:
        if not WHEN_RE.search(full):
            issues.append(_issue("SK-05", "SKILL.md", "description does not say when to use the skill"))
        if PERSON_RE.search(description):
            issues.append(_issue("SK-05", "SKILL.md", "description is not in the third person"))
    return issues


def _check_references(skill: Path, text: str, body: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for target in LINK_RE.findall(body):
        if re.match(r"(https?:|mailto:|#)", target):
            continue
        if "\\" in target:
            issues.append(_issue("SK-13", "SKILL.md", f"backslash in link path {target}"))
        path = target.split("#")[0].replace(SKILL_DIR_VAR, "")
        if path and not (skill / path).exists():
            issues.append(_issue("SK-12", "SKILL.md", f"broken link {target}"))

    docs = sorted(p for p in skill.rglob("*.md") if p.is_file() and p.name != "SKILL.md")
    rel = {p: p.relative_to(skill).as_posix() for p in docs}

    def mentioned(in_text: str, doc: Path) -> bool:
        return rel[doc] in in_text or doc.name in in_text

    first_level = {d for d in docs if mentioned(text, d)}
    for doc in docs:
        doc_text = _read(doc)
        if doc not in first_level:
            parent = next((rel[o] for o in docs if o != doc and mentioned(_read(o), doc)), None)
            message = (f"mentioned only from {parent}, not from SKILL.md (second level)" if parent
                       else "SKILL.md never mentions it (orphan)")
            issues.append(_issue("SK-12", rel[doc], message))
        head = "\n".join(doc_text.splitlines()[:TOC_SEARCH_LINES])
        if doc_text.count("\n") > TOC_FILE_LINES and not TOC_RE.search(head):
            issues.append(_issue("SK-12", rel[doc], f"{doc_text.count(chr(10))} lines without a table of contents at the top"))
        if doc.name == "README.md" and doc.parent == skill:
            issues.append(_issue("SK-13", rel[doc], "README.md in the skill directory"))
    return issues


def _check_script_paths(skill: Path, text: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    files = [p.relative_to(skill).as_posix() for p in skill.rglob("*") if p.is_file() and p.suffix != ".md"]
    for span in _code_spans(text):
        if not re.search(r"\s", span.strip()):
            continue
        for rel in files:
            start = span.find(rel)
            while start != -1:
                if not span[:start].endswith(SKILL_DIR_VAR):
                    issues.append(_issue("SK-15", "SKILL.md",
                                         f"command calls {rel} without ${{CLAUDE_SKILL_DIR}}: {span.strip()[:80]}"))
                    break
                start = span.find(rel, start + 1)
    return issues


def check_skill(skill_dir: str) -> dict[str, Any]:
    skill = Path(skill_dir)
    text = _read(skill / "SKILL.md")
    fm, body = _frontmatter(text)
    result: dict[str, Any] = {
        "name": skill.name, "path": str(skill), "lines": _count_lines(body),
        "description_chars": 0, "manual": False, "issues": [],
    }
    if fm is None or "name" not in fm or "description" not in fm:
        result["issues"].append(_issue("SK-01", "SKILL.md", "no frontmatter, or name / description missing from it"))
        return result

    name = fm["name"]
    manual = fm.get("disable-model-invocation", "").lower() in ("true", "yes", "on", "1")
    result.update(name=name, description_chars=len(fm["description"]), manual=manual)
    issues: list[dict[str, str]] = result["issues"]
    if not NAME_RE.fullmatch(name) or re.search(r"claude|anthropic", name):
        issues.append(_issue("SK-02", "SKILL.md", f"name \"{name}\" breaks the rules: a-z, 0-9, hyphen, up to 64, no claude or anthropic"))
    if name != skill.name:
        issues.append(_issue("SK-02", "SKILL.md", f"name \"{name}\" does not match directory \"{skill.name}\""))
    issues.extend(_check_description(fm, manual))
    if result["lines"] > MAX_BODY_LINES:
        issues.append(_issue("SK-10", "SKILL.md", f"body is {result['lines']} lines > {MAX_BODY_LINES}"))
    issues.extend(_check_references(skill, text, body))
    issues.extend(_check_script_paths(skill, text))
    return result


def check_skills(root: str) -> list[dict[str, Any]]:
    base = Path(root)
    if not base.is_dir():
        return []
    if (base / "SKILL.md").is_file():
        return [check_skill(str(base))]
    results = [
        check_skill(str(d)) for d in sorted(base.iterdir())
        if (d / "SKILL.md").is_file() and not d.name.startswith(AUDIT_SKILL_PREFIX)
    ]
    by_description: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        fm, _ = _frontmatter(_read(Path(result["path"]) / "SKILL.md"))
        description = re.sub(r"\s+", " ", (fm or {}).get("description", "")).strip()
        if description:
            by_description.setdefault(description, []).append(result)
    for group in by_description.values():
        if len(group) > 1:
            for result in group:
                others = ", ".join(r["name"] for r in group if r is not result)
                result["issues"].append(_issue("SK-07", "SKILL.md", f"same description as: {others}"))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    args = parser.parse_args()
    print(json.dumps(check_skills(args.root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
