from __future__ import annotations

import re

from corpus_catalog.config import CatalogConfig
from corpus_catalog.models import ProjectCreationPlan, ProjectPlanFile, SourceRef
from corpus_catalog.naming import (
    CANONICAL_ENTRY_FILENAME,
    CANONICAL_SPEC_ROOT_FILENAME,
    LEGACY_ENTRY_FILENAME,
    LEGACY_SPEC_DIR_NAME,
    LEGACY_SPEC_ROOT_FILENAME,
)
from corpus_catalog.storage import catalog_status, load_index_or_corpus, read_manifest
from corpus_catalog.validators import corpus_baseline


def build_project_creation_plan(
    name: str,
    config: CatalogConfig,
    slug: str | None = None,
    tag: str | None = None,
    tier: str | None = None,
    lifecycle: str = "DRAFT",
) -> ProjectCreationPlan:
    """Return a read-only plan for creating a CORPUS-SPEC-shaped project."""

    project_slug = slug or slugify(name)
    project_path = f"projects/{project_slug}"
    items = load_index_or_corpus(config)
    manifest = read_manifest(config)
    status = catalog_status(config)
    by_path = {item.source.path: item for item in items}
    baseline = manifest.corpus_spec_baseline if manifest else corpus_baseline(items)

    files = [
        ProjectPlanFile(
            path=f"{project_path}/CORPUS.md",
            action="create",
            purpose="Canonical corpus entry point with CORPUS-SPEC conformance frontmatter.",
        ),
        ProjectPlanFile(
            path=f"{project_path}/README.md",
            action="create",
            purpose="Human-facing orientation that points readers to CORPUS.md for state.",
        ),
        ProjectPlanFile(
            path=f"{project_path}/assets/OVERVIEW.md",
            action="create",
            purpose="Project state source of truth: lifecycle, counters, classification, epics, and recommendations.",
        ),
        ProjectPlanFile(
            path=f"{project_path}/assets/reference/",
            action="create",
            purpose="Durable knowledge directory, initially empty unless the project has reusable reference material.",
            required=False,
        ),
        ProjectPlanFile(
            path=f"{project_path}/assets/epics/001-BOOTSTRAP/SPIKE.md",
            action="create",
            purpose="Opening epic design context and eventual closure note.",
        ),
        ProjectPlanFile(
            path=f"{project_path}/assets/epics/001-BOOTSTRAP/TASKS.md",
            action="create",
            purpose="Opening epic task list with the CORPUS-SPEC bookmark convention.",
        ),
        ProjectPlanFile(
            path="CORPUS.md",
            action="update",
            purpose="Add the new project to the tier root's active project table.",
        ),
    ]

    warnings: list[str] = []
    if (config.corpus_root / project_path).exists():
        warnings.append(f"{project_path} already exists.")
    if status.state != "fresh":
        warnings.append(
            "Derived state is not fresh; run catalog index before trusting corpus-wide inventory."
        )

    sources = cite_sources(
        by_path,
        [
            CANONICAL_ENTRY_FILENAME,
            LEGACY_ENTRY_FILENAME,
            f"corpus-spec/{CANONICAL_SPEC_ROOT_FILENAME}",
            f"corpus-spec/{LEGACY_SPEC_ROOT_FILENAME}",
            f"projects/spec/code/corpus-spec/{CANONICAL_SPEC_ROOT_FILENAME}",
            f"projects/spec/code/corpus-spec/{LEGACY_SPEC_ROOT_FILENAME}",
            f"{LEGACY_SPEC_DIR_NAME}/{LEGACY_SPEC_ROOT_FILENAME}",
            f"projects/spec/code/{LEGACY_SPEC_DIR_NAME}/{LEGACY_SPEC_ROOT_FILENAME}",
            f"projects/spec/{CANONICAL_ENTRY_FILENAME}",
            "projects/spec/assets/OVERVIEW.md",
        ],
    )

    return ProjectCreationPlan(
        name=name,
        slug=project_slug,
        project_path=project_path,
        lifecycle=lifecycle,
        tag=tag,
        tier=tier,
        corpus_spec_baseline=baseline,
        files=files,
        sources=sources,
        commands=[
            f"catalog context --cwd {project_path} --goal \"Create project {name}\"",
            "catalog validate --format json",
            "catalog index",
        ],
        notes=[
            "This is a dry-run plan; Catalog did not create or modify files.",
            f"Run suggested commands from the corpus root: {config.corpus_root}.",
            "Use the declared tier-root CORPUS-SPEC baseline for scaffold details.",
            "Keep writes explicit, then validate and refresh .corpus derived state.",
        ],
        warnings=warnings,
    )


def cite_sources(by_path, paths: list[str]) -> list[SourceRef]:
    sources: list[SourceRef] = []
    for path in paths:
        item = by_path.get(path)
        if item is not None:
            sources.append(item.source)
    return sources


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return slug or "new-project"
