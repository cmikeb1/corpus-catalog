from __future__ import annotations

import re
from pathlib import Path

from corpus_catalog.config import (
    CORPUS_IGNORE_FILENAME,
    RECOMMENDED_CORPUSIGNORE_PATTERNS,
    CatalogConfig,
)
from corpus_catalog.corpus import ignore_pattern_matches, load_corpus_ignore_patterns
from corpus_catalog.identity import CorpusIdentityError, extract_current_mount
from corpus_catalog.models import CorpusItem, SourceRef, ValidationIssue
from corpus_catalog.naming import (
    CANONICAL_ENTRY_FILENAME,
    ENTRY_FILENAMES,
    REQUIRED_CORPUS_ENTRY_FIELDS,
    entry_paths,
    field_value,
    has_field,
)


OVERVIEW_REQUIRED_SECTIONS = (
    "Lifecycle Status",
    "Sequence Counters",
    "Classification",
    "Active Epics",
    "Recommendations",
)
HANDBOOK_ENTRY_FILENAMES = frozenset(ENTRY_FILENAMES)
BETA_STEWARDSHIP_RE = re.compile(
    r"Beta stewardship epic:\s*Spec project\s+`?([0-9]{3}-[A-Z0-9][A-Z0-9-]*)`?",
    re.IGNORECASE,
)


def validate_corpus(
    items: list[CorpusItem], config: CatalogConfig
) -> list[ValidationIssue]:
    by_path = {item.source.path: item for item in items}
    baseline = corpus_baseline(items)

    issues: list[ValidationIssue] = []
    issues.extend(validate_core_rules(items, by_path, config, baseline))
    issues.extend(validate_spec_and_profile_rules(items, config, baseline))
    issues.extend(validate_project_profile_rules(items, by_path, baseline))
    issues.extend(validate_workspace_profile_rules(config, by_path, baseline))
    issues.extend(validate_reference_profile_rules(config, by_path, baseline))
    return issues


def validate_core_rules(
    items: list[CorpusItem],
    by_path: dict[str, CorpusItem],
    config: CatalogConfig,
    baseline: str | None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if root_entry_item(by_path) is None:
        issues.append(
            ValidationIssue(
                code="core-missing-root-handbook",
                severity="error",
                message="Corpus root does not contain CORPUS.md or a legacy entry file.",
                source=SourceRef(path=CANONICAL_ENTRY_FILENAME, kind="handbook"),
                baseline=baseline,
            )
        )
    else:
        issues.extend(validate_duplicate_entry_files(by_path, baseline))
        issues.extend(validate_corpus_identity(items, config, baseline))

    issues.extend(validate_corpusignore(config, baseline))

    for item in items:
        if item.source.kind == "handbook":
            missing_fields = [
                field
                for field in REQUIRED_CORPUS_ENTRY_FIELDS
                if not has_field(item.front_matter, field)
            ]
            if missing_fields:
                issues.append(
                    ValidationIssue(
                        code="core-corpus-entry-missing-frontmatter",
                        severity="warning",
                        message=(
                            f"{item.source.path} is missing required CORPUS-SPEC "
                            "frontmatter fields: "
                            + ", ".join(missing_fields)
                        ),
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
                        code="core-component-missing-id",
                        severity="warning",
                        message="Component README has component_type but no component_id.",
                        source=item.source,
                        baseline=baseline,
                    )
                )

    return issues


def validate_corpus_identity(
    items: list[CorpusItem],
    config: CatalogConfig,
    baseline: str | None,
) -> list[ValidationIssue]:
    root_item = root_entry_item({item.source.path: item for item in items})
    if root_item is None:
        return []

    try:
        mount = extract_current_mount(items, config)
    except CorpusIdentityError as error:
        return [
            ValidationIssue(
                code="core-corpus-identity-invalid",
                severity="warning",
                message=str(error),
                source=root_item.source,
                baseline=baseline,
            )
        ]

    if mount is None:
        return [
            ValidationIssue(
                code="core-corpus-identity-missing",
                severity="warning",
                message=(
                    "Tier root does not declare corpus URI, mount URI, "
                    "owner, realm, tier, node, and sync transport fields."
                ),
                source=root_item.source,
                baseline=baseline,
            )
        ]

    return []


def validate_spec_and_profile_rules(
    items: list[CorpusItem], config: CatalogConfig, baseline: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    spec_project_exists = spec_project_present(config)

    for item in items:
        if item.source.kind not in {"spec-module", "profile-module"}:
            continue
        if not is_spec_owned_module(item):
            continue
        if str(field_value(item.front_matter, "corpus_spec_status") or "").casefold() != "beta":
            continue

        code_prefix = "spec" if item.source.kind == "spec-module" else "profile"
        epic_code = beta_stewardship_epic(item.text)
        if epic_code is None:
            issues.append(
                ValidationIssue(
                    code=f"{code_prefix}-beta-missing-stewardship-epic",
                    severity="warning",
                    message=(
                        "Beta spec/profile module does not name an owning "
                        "Spec epic."
                    ),
                    source=item.source,
                    baseline=baseline,
                )
            )
            continue

        if spec_project_exists and not spec_epic_dir_exists(config, epic_code):
            issues.append(
                ValidationIssue(
                    code=f"{code_prefix}-beta-stewardship-epic-missing",
                    severity="warning",
                    message=(
                        "Beta spec/profile module names Spec epic "
                        f"{epic_code}, but that epic directory is missing."
                    ),
                    source=item.source,
                    baseline=baseline,
                )
            )

    return issues


def validate_project_profile_rules(
    items: list[CorpusItem],
    by_path: dict[str, CorpusItem],
    baseline: str | None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for item in items:
        if (
            is_project_handbook(item)
            and project_overview_required(item)
            and not project_overview_exists(item, by_path)
        ):
            issues.append(
                ValidationIssue(
                    code="profile-project-missing-overview",
                    severity="warning",
                    message=(
                        "Project corpus entry exists but assets/OVERVIEW.md "
                        "is missing."
                    ),
                    source=item.source,
                    baseline=baseline,
                )
            )

        if item.source.kind == "overview" and is_project_overview(item):
            for section in OVERVIEW_REQUIRED_SECTIONS:
                if not has_heading(item.text, section):
                    issues.append(
                        ValidationIssue(
                            code="profile-project-overview-missing-section",
                            severity="warning",
                            message=f"Project OVERVIEW.md is missing section: {section}.",
                            source=item.source,
                            baseline=baseline,
                        )
                    )

        if item.source.kind == "tasks" and "BOOKMARK" not in item.text:
            issues.append(
                ValidationIssue(
                    code="profile-project-tasks-missing-bookmark",
                    severity="warning",
                    message="Epic TASKS.md does not contain a BOOKMARK marker.",
                    source=item.source,
                    baseline=baseline,
                )
            )

    return issues


def validate_workspace_profile_rules(
    config: CatalogConfig, by_path: dict[str, CorpusItem], baseline: str | None
) -> list[ValidationIssue]:
    if not workspace_profile_active(config, by_path):
        return []

    issues: list[ValidationIssue] = []
    required_files = (
        (
            "workspace/kanban.md",
            "profile-workspace-missing-kanban",
            "Workspace profile is active but workspace/kanban.md is missing.",
        ),
        (
            "workspace/inbox.md",
            "profile-workspace-missing-inbox",
            "Workspace profile is active but workspace/inbox.md is missing.",
        ),
    )
    for path, code, message in required_files:
        if not corpus_path_exists(config, by_path, path):
            issues.append(
                ValidationIssue(
                    code=code,
                    severity="warning",
                    message=message,
                    source=SourceRef(path=path, kind="note"),
                    baseline=baseline,
                )
            )
    return issues


def validate_reference_profile_rules(
    config: CatalogConfig, by_path: dict[str, CorpusItem], baseline: str | None
) -> list[ValidationIssue]:
    if not reference_profile_active(config, by_path):
        return []

    issues: list[ValidationIssue] = []
    if not reference_entry_exists(config, by_path, "reference"):
        issues.append(
            ValidationIssue(
                code="profile-reference-missing-root-entry",
                severity="warning",
                message=(
                    "Reference profile is active but reference/CORPUS.md "
                    "or a legacy reference entry file is missing."
                ),
                source=SourceRef(path="reference/CORPUS.md", kind="handbook"),
                baseline=baseline,
            )
        )

    reference_root = config.corpus_root / "reference"
    if not reference_root.exists():
        return issues

    for directory in sorted(reference_root.rglob("*")):
        if not directory.is_dir() or path_has_excluded_part(config, directory):
            continue
        if not reference_section_has_content(config, directory):
            continue

        rel_path = config.relative_path(directory)
        if reference_entry_exists(config, by_path, rel_path):
            continue
        issues.append(
            ValidationIssue(
                code="profile-reference-subsection-missing-entry",
                severity="warning",
                message=(
                    "Reference subsection is missing CORPUS.md or a legacy "
                    "profile entry."
                ),
                source=SourceRef(path=f"{rel_path}/CORPUS.md", kind="handbook"),
                baseline=baseline,
            )
        )

    return issues


def validate_corpusignore(
    config: CatalogConfig, baseline: str | None
) -> list[ValidationIssue]:
    existing_recommended = [
        pattern
        for pattern in RECOMMENDED_CORPUSIGNORE_PATTERNS
        if (config.corpus_root / pattern.rstrip("/")).exists()
    ]
    if not existing_recommended:
        return []

    source = SourceRef(path=CORPUS_IGNORE_FILENAME, kind="note")
    if not config.corpus_ignore_path.exists():
        return [
            ValidationIssue(
                code="core-corpusignore-missing",
                severity="warning",
                message=(
                    "Corpus has package-local code paths that should be "
                    f"excluded; add {CORPUS_IGNORE_FILENAME} with recommended "
                    "rules."
                ),
                source=source,
                baseline=baseline,
            )
        ]

    patterns = load_corpus_ignore_patterns(config)
    missing = [
        pattern
        for pattern in existing_recommended
        if not corpusignore_covers_recommended_pattern(pattern, patterns)
    ]
    if not missing:
        return []

    return [
        ValidationIssue(
            code="core-corpusignore-missing-recommended-rule",
            severity="warning",
            message=(
                f"{CORPUS_IGNORE_FILENAME} is missing recommended package-local "
                "code exclusions: " + ", ".join(missing)
            ),
            source=source,
            baseline=baseline,
        )
    ]


def corpusignore_covers_recommended_pattern(
    recommended_pattern: str, ignore_patterns: tuple[str, ...]
) -> bool:
    sample = f"{recommended_pattern.rstrip('/')}/README.md"
    return any(
        ignore_pattern_matches(sample, pattern)
        or ignore_pattern_matches(recommended_pattern.rstrip("/"), pattern)
        for pattern in ignore_patterns
    )


def root_entry_item(by_path: dict[str, CorpusItem]) -> CorpusItem | None:
    for path in entry_paths():
        item = by_path.get(path)
        if item is not None:
            return item
    return None


def validate_duplicate_entry_files(
    by_path: dict[str, CorpusItem], baseline: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    scopes: dict[str, list[str]] = {}
    for path in by_path:
        parts = path.split("/")
        if parts[-1] not in ENTRY_FILENAMES:
            continue
        scope = "/".join(parts[:-1])
        scopes.setdefault(scope, []).append(path)

    for paths in scopes.values():
        if len(paths) <= 1 or not any(path.endswith("/CORPUS.md") or path == "CORPUS.md" for path in paths):
            continue
        issues.append(
            ValidationIssue(
                code="core-corpus-entry-duplicate-legacy",
                severity="warning",
                message=(
                    "CORPUS.md and a legacy entry file both exist for the "
                    "same scope; prefer CORPUS.md and remove the legacy entry "
                    "after migration."
                ),
                source=SourceRef(path=sorted(paths)[0], kind="handbook"),
                baseline=baseline,
            )
        )
    return issues


def beta_stewardship_epic(text: str) -> str | None:
    match = BETA_STEWARDSHIP_RE.search(text)
    if match is None:
        return None
    return match.group(1).upper()


def spec_project_present(config: CatalogConfig) -> bool:
    return (config.corpus_root / "projects" / "spec").exists()


def spec_epic_dir_exists(config: CatalogConfig, epic_code: str) -> bool:
    epic_root = config.corpus_root / "projects" / "spec" / "assets" / "epics"
    if not epic_root.exists():
        return False
    return any(
        child.is_dir()
        and (
            child.name.casefold() == epic_code.casefold()
            or child.name.casefold().startswith(f"{epic_code.casefold()}-")
        )
        for child in epic_root.iterdir()
    )


def is_spec_owned_module(item: CorpusItem) -> bool:
    return item.source.path.startswith(
        (
            "projects/spec/code/corpus-spec/specs/",
            "projects/spec/code/corpus-spec/profiles/",
            "projects/spec/code/corpus-spec/specs/",
            "projects/spec/code/corpus-spec/profiles/",
        )
    )


def corpus_path_exists(
    config: CatalogConfig, by_path: dict[str, CorpusItem], rel_path: str
) -> bool:
    return rel_path in by_path or (config.corpus_root / rel_path).exists()


def workspace_profile_active(
    config: CatalogConfig, by_path: dict[str, CorpusItem]
) -> bool:
    return (config.corpus_root / "workspace").exists() or any(
        path.startswith("workspace/") for path in by_path
    )


def reference_profile_active(
    config: CatalogConfig, by_path: dict[str, CorpusItem]
) -> bool:
    return (config.corpus_root / "reference").exists() or any(
        path.startswith("reference/") for path in by_path
    )


def reference_entry_exists(
    config: CatalogConfig, by_path: dict[str, CorpusItem], section_path: str
) -> bool:
    return any(
        corpus_path_exists(config, by_path, f"{section_path}/{filename}")
        for filename in HANDBOOK_ENTRY_FILENAMES
    )


def reference_section_has_content(config: CatalogConfig, directory: Path) -> bool:
    for child in directory.rglob("*"):
        if not child.is_file() or path_has_excluded_part(config, child):
            continue
        if child.name in HANDBOOK_ENTRY_FILENAMES:
            continue
        return True
    return False


def path_has_excluded_part(config: CatalogConfig, path: Path) -> bool:
    rel_parts = path.resolve().relative_to(config.corpus_root).parts
    return any(
        part in config.exclude_parts or part.startswith(".") for part in rel_parts
    )


def is_project_handbook(item: CorpusItem) -> bool:
    parts = item.source.path.split("/")
    return (
        len(parts) == 3
        and parts[0] == "projects"
        and parts[2] in HANDBOOK_ENTRY_FILENAMES
    )


def project_overview_required(item: CorpusItem) -> bool:
    profile = field_value(item.front_matter, "corpus_spec_profile")
    adoption = field_value(item.front_matter, "corpus_spec_adoption")
    return not (profile == "project-shell" and adoption == "pre-spec")


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
    root_item = root_entry_item(by_path)
    if root_item is not None:
        root_version = field_value(root_item.front_matter, "corpus_spec_version")
        if root_version:
            return str(root_version)

    for item in sorted(items, key=lambda candidate: candidate.source.path):
        version = field_value(item.front_matter, "corpus_spec_version")
        if version:
            return str(version)
    return None
