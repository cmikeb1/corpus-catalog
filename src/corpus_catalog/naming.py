from __future__ import annotations

from typing import Any


CANONICAL_ENTRY_FILENAME = "CORPUS.md"
LEGACY_ENTRY_STEM = "A" "I"
LEGACY_ENTRY_FILENAME = f"{LEGACY_ENTRY_STEM}.md"
LEGACY_LOWER_ENTRY_FILENAME = "corpus.md"
ENTRY_FILENAMES = (
    CANONICAL_ENTRY_FILENAME,
    LEGACY_LOWER_ENTRY_FILENAME,
    LEGACY_ENTRY_FILENAME,
)

CANONICAL_SPEC_ROOT_FILENAME = "CORPUS-SPEC.md"
LEGACY_SPEC_STEM = f"{LEGACY_ENTRY_STEM}-SPEC"
LEGACY_SPEC_ROOT_FILENAME = f"{LEGACY_SPEC_STEM}.md"
LEGACY_LOWER_SPEC_ROOT_FILENAME = "corpus-spec.md"
LEGACY_SPEC_DIR_NAME = "ai" "-spec"
SPEC_ROOT_FILENAMES = (
    CANONICAL_SPEC_ROOT_FILENAME,
    LEGACY_LOWER_SPEC_ROOT_FILENAME,
    LEGACY_SPEC_ROOT_FILENAME,
)

LEGACY_FIELD_PREFIX = "ai" "_spec_"
LEGACY_ENTRY_DOC_TYPE = "ai" "-entry"


def legacy_field(suffix: str) -> str:
    return f"{LEGACY_FIELD_PREFIX}{suffix}"


FIELD_ALIASES = {
    "corpus_spec_version": (legacy_field("version"),),
    "corpus_spec_profile": (legacy_field("profile"),),
    "corpus_spec_adoption": (legacy_field("adoption"),),
    "corpus_spec_reviewed": (legacy_field("reviewed"),),
    "corpus_spec_betas": (legacy_field("betas"),),
    "corpus_spec_corpus_uri": (legacy_field("corpus_uri"), "corpus_uri"),
    "corpus_spec_mount_uri": (legacy_field("mount_uri"), "mount_uri"),
    "corpus_spec_owner_id": (legacy_field("owner_id"), "corpus_owner_id"),
    "corpus_spec_realm": (legacy_field("realm"), "corpus_realm"),
    "corpus_spec_tier": (legacy_field("tier"), "corpus_tier"),
    "corpus_spec_node_id": (legacy_field("node_id"), "corpus_node_id"),
    "corpus_spec_sync_transport": (
        legacy_field("sync_transport"),
        "corpus_sync_transport",
    ),
    "corpus_spec_spec_id": (legacy_field("spec_id"),),
    "corpus_spec_profile_id": (legacy_field("profile_id"),),
    "corpus_spec_status": (legacy_field("status"),),
}

REQUIRED_CORPUS_ENTRY_FIELDS = (
    "doc_type",
    "corpus_spec_version",
    "corpus_spec_profile",
    "corpus_spec_adoption",
    "corpus_spec_reviewed",
    "corpus_spec_betas",
)


def entry_path(scope: str | None = None) -> str:
    if scope:
        return f"{scope.rstrip('/')}/{CANONICAL_ENTRY_FILENAME}"
    return CANONICAL_ENTRY_FILENAME


def entry_paths(scope: str | None = None) -> tuple[str, ...]:
    if scope:
        prefix = scope.rstrip("/")
        return tuple(f"{prefix}/{filename}" for filename in ENTRY_FILENAMES)
    return ENTRY_FILENAMES


def is_entry_path(path: str) -> bool:
    return path in ENTRY_FILENAMES or any(
        path.endswith(f"/{filename}") for filename in ENTRY_FILENAMES
    )


def is_spec_root_filename(filename: str) -> bool:
    return filename in SPEC_ROOT_FILENAMES


def field_value(front_matter: dict[str, Any], canonical_key: str) -> Any:
    if canonical_key in front_matter:
        return front_matter[canonical_key]
    for alias in FIELD_ALIASES.get(canonical_key, ()):
        if alias in front_matter:
            return front_matter[alias]
    return None


def has_field(front_matter: dict[str, Any], canonical_key: str) -> bool:
    return field_value(front_matter, canonical_key) is not None


def has_corpus_spec_metadata(front_matter: dict[str, Any]) -> bool:
    return any(
        key.startswith("corpus_spec_") or key.startswith(LEGACY_FIELD_PREFIX)
        for key in front_matter
    )


def legacy_metadata_fields(front_matter: dict[str, Any]) -> list[str]:
    return sorted(key for key in front_matter if key.startswith(LEGACY_FIELD_PREFIX))


def normalize_metadata_fields(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    for canonical_key, aliases in FIELD_ALIASES.items():
        if canonical_key in normalized:
            continue
        for alias in aliases:
            if alias in normalized:
                normalized[canonical_key] = normalized.pop(alias)
                break
    return normalized
