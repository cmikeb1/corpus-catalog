from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.models import CorpusItem, SourceRef


def load_corpus(config: CatalogConfig) -> list[CorpusItem]:
    """Load candidate Markdown files from a corpus root."""

    items: list[CorpusItem] = []
    for path in _iter_markdown_paths(config):
        items.append(load_markdown_item(path, config))
    return sorted(items, key=lambda item: item.source.path)


def load_markdown_item(path: Path, config: CatalogConfig) -> CorpusItem:
    raw = path.read_text(encoding="utf-8")
    front_matter, body, body_line = parse_front_matter(raw)
    rel_path = config.relative_path(path)
    title, title_line = find_title(body, body_line)
    kind = source_kind(rel_path)
    excerpt = first_non_empty_line(body)
    line_count = raw.count("\n") + 1

    source = SourceRef(
        path=rel_path,
        kind=kind,
        title=title,
        line_start=title_line or 1,
        line_end=line_count,
        excerpt=excerpt,
    )
    return CorpusItem(
        source=source,
        title=title or rel_path,
        front_matter=front_matter,
        text=body.strip(),
    )


def search_corpus(
    query: str, items: list[CorpusItem], limit: int = 10
) -> list[CorpusItem]:
    """Simple lexical search over path, title, front matter, and text."""

    terms = [term.casefold() for term in query.split() if term.strip()]
    if not terms:
        return []

    scored: list[tuple[int, CorpusItem]] = []
    for item in items:
        haystack = "\n".join(
            [
                item.source.path,
                item.title,
                " ".join(str(value) for value in item.front_matter.values()),
                item.text,
            ]
        ).casefold()
        score = sum(haystack.count(term) for term in terms)
        if score:
            scored.append((score, item))

    scored.sort(key=lambda pair: (-pair[0], pair[1].source.path))
    return [item for _, item in scored[:limit]]


def parse_front_matter(raw: str) -> tuple[dict[str, Any], str, int]:
    """Parse a small YAML-style front matter subset.

    This intentionally avoids making full YAML a core dependency. It
    supports the simple scalar and list forms currently used by
    AI-SPEC handbooks and component-style metadata.
    """

    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw, 1

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, raw, 1

    front_matter = parse_simple_yaml(lines[1:end_index])
    body_lines = lines[end_index + 1 :]
    return front_matter, "\n".join(body_lines), end_index + 2


def parse_simple_yaml(lines: list[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        stripped = line.strip()
        if current_key and stripped.startswith("- "):
            data.setdefault(current_key, []).append(parse_scalar(stripped[2:].strip()))
            continue

        current_key = None
        if ":" not in line:
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not value:
            data[key] = []
            current_key = key
        else:
            data[key] = parse_scalar(value)

    return data


def parse_scalar(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit():
        return int(value)
    return value.strip("'\"")


def find_title(body: str, body_start_line: int) -> tuple[str | None, int | None]:
    for offset, line in enumerate(body.splitlines(), start=0):
        if line.startswith("# "):
            return line[2:].strip(), body_start_line + offset
    return None, None


def first_non_empty_line(body: str) -> str | None:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:240]
    return None


def source_kind(rel_path: str):
    if rel_path == "AI.md" or rel_path.endswith("/AI.md"):
        return "handbook"
    if rel_path.endswith("/assets/OVERVIEW.md"):
        return "overview"
    if rel_path.endswith("/TASKS.md") and "/assets/epics/" in rel_path:
        return "tasks"
    if "/registry/" in rel_path:
        return "registry"
    if rel_path.endswith("/README.md"):
        return "readme"
    if rel_path.startswith("ai-spec/"):
        return "spec"
    return "note"


def _iter_markdown_paths(config: CatalogConfig):
    for path in config.corpus_root.rglob("*.md"):
        if not path.is_file():
            continue
        if any(part in config.exclude_parts for part in path.parts):
            continue

        rel_path = config.relative_path(path)
        if any(fnmatch(rel_path, pattern) for pattern in config.include_patterns):
            yield path
