from __future__ import annotations

from pathlib import Path

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.corpus import search_corpus, source_fingerprint
from ai_spec_catalog.models import CatalogQuery, ContextItem, ContextPacket, CorpusItem
from ai_spec_catalog.storage import load_index_or_corpus, read_manifest
from ai_spec_catalog.validators import corpus_baseline, validate_corpus


def build_context_packet(
    goal: str,
    cwd: str | Path | None,
    config: CatalogConfig,
) -> ContextPacket:
    """Assemble a source-cited context packet for an agent task."""

    items = load_index_or_corpus(config)
    selected = select_context_items(goal, cwd, items, config)
    issues = validate_corpus(items, config)
    manifest = read_manifest(config)

    return ContextPacket(
        query=CatalogQuery(goal=goal, cwd=str(cwd) if cwd is not None else None),
        items=[to_context_item(item, config) for item in selected],
        validation_issues=issues,
        guidance=[
            "Treat source corpus files as canonical.",
            "Use generated context as a bounded starting point, not as memory.",
            "Keep write workflows explicit: propose, validate, diff, approve, apply.",
        ],
        baseline=manifest.ai_spec_baseline if manifest else corpus_baseline(items),
        source_fingerprint=(
            manifest.source_fingerprint if manifest else source_fingerprint(items)
        ),
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

        spike_path = nearest_spike_path(cwd_path)
        if spike_path:
            add(spike_path)

    for routed_path in routed_profile_and_spec_paths(goal, cwd_path, items):
        add(routed_path)

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


def routed_profile_and_spec_paths(
    goal: str,
    cwd_path: Path | None,
    items: list[CorpusItem],
) -> list[str]:
    paths: list[str] = []

    def add_module(module_type: str, module_id: str) -> None:
        item = best_module_item(items, module_type, module_id)
        if item and item.source.path not in paths:
            paths.append(item.source.path)

    for profile_id in profile_ids_for_cwd(cwd_path):
        add_module("profile", profile_id)

    routing_text = routing_haystack(goal, cwd_path)
    if any(term in routing_text for term in TOOLING_SPEC_TERMS):
        add_module("spec", "tooling-and-validation")

    if any(term in routing_text for term in PROFILE_COMPOSITION_TERMS):
        add_module("spec", "profile-composition")

    if any(term in routing_text for term in CORPUS_IDENTITY_TERMS):
        add_module("spec", "corpus-identity")

    return paths


TOOLING_SPEC_TERMS = (
    "catalog",
    "generated state",
    "generated-state",
    "index",
    "indexing",
    "source sync",
    "source-sync",
    "source synchronization",
    "source-synchronization",
    "validate",
    "validation",
)

PROFILE_COMPOSITION_TERMS = (
    "active profile",
    "active profiles",
    "beta",
    "betas",
    "module",
    "modules",
    "package",
    "packaging",
    "profile",
    "profiles",
)

CORPUS_IDENTITY_TERMS = (
    "--corpus",
    "--mount",
    "corpus identity",
    "corpus uri",
    "corpus://",
    "mount identity",
    "mount inventory",
    "mount uri",
    "node id",
    "realm",
    "sync transport",
)


def profile_ids_for_cwd(cwd_path: Path | None) -> tuple[str, ...]:
    if cwd_path is None:
        return ()

    rel = cwd_path.as_posix()
    if rel == "reference/initiatives" or rel.startswith("reference/initiatives/"):
        return ("reference", "initiatives")
    if rel == "reference" or rel.startswith("reference/"):
        return ("reference",)
    if rel == "workspace" or rel.startswith("workspace/"):
        return ("human-workspace",)
    if rel == "projects" or rel.startswith("projects/"):
        return ("project",)
    return ()


def routing_haystack(goal: str, cwd_path: Path | None) -> str:
    parts = [goal]
    if cwd_path is not None:
        parts.append(cwd_path.as_posix())
    return " ".join(parts).replace("_", "-").casefold()


def best_module_item(
    items: list[CorpusItem],
    module_type: str,
    module_id: str,
) -> CorpusItem | None:
    matches = [
        item
        for item in items
        if item.source.kind in ("profile-module", "spec-module")
        and module_type_for_item(item) == module_type
        and module_id_for_item(item) == module_id
    ]
    if not matches:
        return None

    return min(matches, key=module_preference_rank)


def module_type_for_item(item: CorpusItem) -> str | None:
    if item.source.kind == "profile-module":
        return "profile"
    if item.source.kind == "spec-module":
        return "spec"
    return None


def module_id_for_item(item: CorpusItem) -> str:
    if item.source.kind == "profile-module":
        value = item.front_matter.get("ai_spec_profile_id")
    else:
        value = item.front_matter.get("ai_spec_spec_id")

    if value:
        return str(value)
    return Path(item.source.path).stem


def module_preference_rank(item: CorpusItem) -> tuple[int, str]:
    path = item.source.path
    preferred_prefixes = (
        "projects/spec/code/corpus-spec/",
        "projects/spec/code/ai-spec/",
        "corpus-spec/",
        "ai-spec/",
    )
    for index, prefix in enumerate(preferred_prefixes):
        if path.startswith(prefix):
            return (index, path)
    return (len(preferred_prefixes), path)


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


def nearest_spike_path(cwd_path: Path) -> str | None:
    parts = list(cwd_path.parts)
    try:
        epics_index = parts.index("epics")
    except ValueError:
        return None

    if len(parts) <= epics_index + 1:
        return None

    return Path(*parts[: epics_index + 2], "SPIKE.md").as_posix()
