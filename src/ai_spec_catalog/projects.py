from __future__ import annotations

import re

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.models import ProjectCreationPlan, ProjectPlanFile, SourceRef
from ai_spec_catalog.storage import catalog_status, load_index_or_corpus, read_manifest
from ai_spec_catalog.validators import corpus_baseline


def build_project_creation_plan(
    name: str,
    config: CatalogConfig,
    slug: str | None = None,
    tag: str | None = None,
    tier: str | None = None,
    lifecycle: str = "DRAFT",
) -> ProjectCreationPlan:
    """Return a read-only plan for creating an AI-SPEC-shaped project."""

    project_slug = slug or slugify(name)
    project_path = f"projects/{project_slug}"
    items = load_index_or_corpus(config)
    manifest = read_manifest(config)
    status = catalog_status(config)
    by_path = {item.source.path: item for item in items}
    baseline = manifest.ai_spec_baseline if manifest else corpus_baseline(items)

    files = [
        ProjectPlanFile(
            path=f"{project_path}/AI.md",
            action="create",
            purpose="Canonical AI entry point with AI-SPEC conformance frontmatter.",
        ),
        ProjectPlanFile(
            path=f"{project_path}/README.md",
            action="create",
            purpose="Human-facing orientation that points readers to AI.md for state.",
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
            purpose="Opening epic task list with the AI-SPEC bookmark convention.",
        ),
        ProjectPlanFile(
            path="AI.md",
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
            "AI.md",
            "corpus-spec/AI-SPEC.md",
            "projects/spec/code/corpus-spec/AI-SPEC.md",
            "ai-spec/AI-SPEC.md",
            "projects/spec/code/ai-spec/AI-SPEC.md",
            "projects/spec/AI.md",
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
        ai_spec_baseline=baseline,
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
            "Use the declared tier-root AI-SPEC baseline for scaffold details.",
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
