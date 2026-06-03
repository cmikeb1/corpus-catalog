from __future__ import annotations

from cans_catalog.config import CatalogConfig
from cans_catalog.models import CorpusItem, SourceRef, ValidationIssue


def validate_corpus(
    items: list[CorpusItem], config: CatalogConfig
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    by_path = {item.source.path: item for item in items}

    if "AI.md" not in by_path:
        issues.append(
            ValidationIssue(
                code="missing-root-handbook",
                severity="error",
                message="Corpus root does not contain AI.md.",
                source=SourceRef(path="AI.md", kind="handbook"),
            )
        )

    for item in items:
        if item.source.kind == "tasks" and "BOOKMARK" not in item.text:
            issues.append(
                ValidationIssue(
                    code="tasks-missing-bookmark",
                    severity="warning",
                    message="Epic TASKS.md does not contain a BOOKMARK marker.",
                    source=item.source,
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
                    )
                )

    return issues
