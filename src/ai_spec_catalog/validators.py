from __future__ import annotations

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.models import CorpusItem, SourceRef, ValidationIssue


AI_REQUIRED_FRONTMATTER = (
    "doc_type",
    "ai_spec_version",
    "ai_spec_profile",
    "ai_spec_adoption",
    "ai_spec_reviewed",
    "ai_spec_betas",
)
OVERVIEW_REQUIRED_SECTIONS = (
    "Lifecycle Status",
    "Sequence Counters",
    "Classification",
    "Active Epics",
    "Recommendations",
)


def validate_corpus(
    items: list[CorpusItem], config: CatalogConfig
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    by_path = {item.source.path: item for item in items}
    baseline = corpus_baseline(items)

    if "AI.md" not in by_path:
        issues.append(
            ValidationIssue(
                code="missing-root-handbook",
                severity="error",
                message="Corpus root does not contain AI.md.",
                source=SourceRef(path="AI.md", kind="handbook"),
                baseline=baseline,
            )
        )

    for item in items:
        if item.source.kind == "handbook":
            missing_fields = [
                field
                for field in AI_REQUIRED_FRONTMATTER
                if field not in item.front_matter
            ]
            if missing_fields:
                issues.append(
                    ValidationIssue(
                        code="ai-handbook-missing-frontmatter",
                        severity="warning",
                        message=(
                            "AI.md is missing required AI-SPEC frontmatter fields: "
                            + ", ".join(missing_fields)
                        ),
                        source=item.source,
                        baseline=baseline,
                    )
                )

        if is_project_handbook(item) and not project_overview_exists(item, by_path):
            issues.append(
                ValidationIssue(
                    code="project-missing-overview",
                    severity="warning",
                    message="Project AI.md exists but assets/OVERVIEW.md is missing.",
                    source=item.source,
                    baseline=baseline,
                )
            )

        if item.source.kind == "overview" and is_project_overview(item):
            for section in OVERVIEW_REQUIRED_SECTIONS:
                if not has_heading(item.text, section):
                    issues.append(
                        ValidationIssue(
                            code="project-overview-missing-section",
                            severity="warning",
                            message=f"Project OVERVIEW.md is missing section: {section}.",
                            source=item.source,
                            baseline=baseline,
                        )
                    )

        if item.source.kind == "tasks" and "BOOKMARK" not in item.text:
            issues.append(
                ValidationIssue(
                    code="tasks-missing-bookmark",
                    severity="warning",
                    message="Epic TASKS.md does not contain a BOOKMARK marker.",
                    source=item.source,
                    baseline=baseline,
                )
            )

        if item.source.kind == "readme":
            component_type = item.front_matter.get("component_type")
            component_id = item.front_matter.get("component_id")
            if component_type and not component_id:
                issues.append(
                    ValidationIssue(
                        code="component-missing-id",
                        severity="warning",
                        message="Component README has component_type but no component_id.",
                        source=item.source,
                        baseline=baseline,
                    )
                )

    return issues


def is_project_handbook(item: CorpusItem) -> bool:
    parts = item.source.path.split("/")
    return len(parts) == 3 and parts[0] == "projects" and parts[2] == "AI.md"


def project_overview_exists(
    item: CorpusItem, by_path: dict[str, CorpusItem]
) -> bool:
    project = item.source.path.split("/")[1]
    return f"projects/{project}/assets/OVERVIEW.md" in by_path


def is_project_overview(item: CorpusItem) -> bool:
    parts = item.source.path.split("/")
    return (
        len(parts) == 4
        and parts[0] == "projects"
        and parts[2] == "assets"
        and parts[3] == "OVERVIEW.md"
    )


def has_heading(text: str, heading: str) -> bool:
    target = heading.casefold()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") and stripped.lstrip("#").strip().casefold() == target:
            return True
    return False


def corpus_baseline(items: list[CorpusItem]) -> str | None:
    by_path = {item.source.path: item for item in items}
    root_item = by_path.get("AI.md")
    if root_item is not None:
        root_version = root_item.front_matter.get("ai_spec_version")
        if root_version:
            return str(root_version)

    for item in sorted(items, key=lambda candidate: candidate.source.path):
        version = item.front_matter.get("ai_spec_version")
        if version:
            return str(version)
    return None
