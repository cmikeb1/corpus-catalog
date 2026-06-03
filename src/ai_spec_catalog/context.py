from __future__ import annotations

from pathlib import Path

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.corpus import load_corpus, search_corpus
from ai_spec_catalog.models import CatalogQuery, ContextItem, ContextPacket, CorpusItem
from ai_spec_catalog.validators import validate_corpus


def build_context_packet(
    goal: str,
    cwd: str | Path | None,
    config: CatalogConfig,
) -> ContextPacket:
    """Assemble a source-cited context packet for an agent task."""

    items = load_corpus(config)
    selected = select_context_items(goal, cwd, items, config)
    issues = validate_corpus(items, config)

    return ContextPacket(
        query=CatalogQuery(goal=goal, cwd=str(cwd) if cwd is not None else None),
        items=[to_context_item(item, config) for item in selected],
        validation_issues=issues,
        guidance=[
            "Treat source corpus files as canonical.",
            "Use generated context as a bounded starting point, not as memory.",
            "Keep write workflows explicit: propose, validate, diff, approve, apply.",
        ],
    )


def select_context_items(
    goal: str,
    cwd: str | Path | None,
    items: list[CorpusItem],
    config: CatalogConfig,
) -> list[CorpusItem]:
    by_path = {item.source.path: item for item in items}
    selected: list[CorpusItem] = []
    cwd_path = normalize_cwd(cwd, config)

    def add(path: str) -> None:
        item = by_path.get(path)
        if item and item not in selected:
            selected.append(item)

    add("AI.md")

    if cwd_path is not None:
        for handbook_path in cascading_handbooks(cwd_path, config):
            add(handbook_path)

        project_path = project_overview_path(cwd_path)
        if project_path:
            add(project_path)

        task_path = nearest_task_path(cwd_path)
        if task_path:
            add(task_path)

    if any(
        term in goal.casefold()
        for term in ("integration", "adapter", "deployment", "persona", "registry")
    ):
        for item in items:
            if item.source.kind == "registry":
                add(item.source.path)

    for item in search_corpus(goal, items, limit=config.max_context_items):
        add(item.source.path)
        if len(selected) >= config.max_context_items:
            break

    return selected[: config.max_context_items]


def to_context_item(item: CorpusItem, config: CatalogConfig) -> ContextItem:
    text = item.text.strip()
    limit = config.max_context_item_chars
    if len(text) > limit:
        text = text[:limit].rstrip() + "\n[truncated; read source for full text]"

    return ContextItem(
        source=item.source,
        title=item.title,
        front_matter=item.front_matter,
        excerpt=text,
    )


def normalize_cwd(cwd: str | Path | None, config: CatalogConfig) -> Path | None:
    if cwd is None:
        return None

    path = Path(cwd).expanduser()
    if not path.is_absolute():
        path = config.corpus_root / path

    try:
        return path.resolve().relative_to(config.corpus_root)
    except ValueError:
        return None


def cascading_handbooks(cwd_path: Path, config: CatalogConfig) -> list[str]:
    paths = ["AI.md"]
    parts = list(cwd_path.parts)
    for index in range(1, len(parts) + 1):
        candidate = Path(*parts[:index]) / "AI.md"
        paths.append(candidate.as_posix())
    return paths


def project_overview_path(cwd_path: Path) -> str | None:
    parts = list(cwd_path.parts)
    if len(parts) >= 2 and parts[0] == "projects":
        return Path("projects", parts[1], "assets", "OVERVIEW.md").as_posix()
    return None


def nearest_task_path(cwd_path: Path) -> str | None:
    parts = list(cwd_path.parts)
    try:
        epics_index = parts.index("epics")
    except ValueError:
        return None

    if len(parts) <= epics_index + 1:
        return None

    return Path(*parts[: epics_index + 2], "TASKS.md").as_posix()
