from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from corpus_catalog.naming import (
    CANONICAL_ENTRY_FILENAME,
    CANONICAL_SPEC_ROOT_FILENAME,
    LEGACY_ENTRY_FILENAME,
    LEGACY_LOWER_ENTRY_FILENAME,
    LEGACY_LOWER_SPEC_ROOT_FILENAME,
    LEGACY_SPEC_DIR_NAME,
    LEGACY_SPEC_ROOT_FILENAME,
)


DEFAULT_INCLUDE_PATTERNS = (
    CANONICAL_ENTRY_FILENAME,
    f"**/{CANONICAL_ENTRY_FILENAME}",
    LEGACY_ENTRY_FILENAME,
    f"**/{LEGACY_ENTRY_FILENAME}",
    LEGACY_LOWER_ENTRY_FILENAME,
    f"**/{LEGACY_LOWER_ENTRY_FILENAME}",
    "**/README.md",
    "**/assets/OVERVIEW.md",
    "**/assets/epics/*/TASKS.md",
    "**/assets/epics/*/SPIKE.md",
    "**/assets/epics/*/reference/*.md",
    "**/assets/epics/*/reference/**/*.md",
    "**/assets/reference/*.md",
    "**/assets/reference/**/*.md",
    "**/registry/*.md",
    f"corpus-spec/{CANONICAL_SPEC_ROOT_FILENAME}",
    f"corpus-spec/{LEGACY_SPEC_ROOT_FILENAME}",
    f"corpus-spec/{LEGACY_LOWER_SPEC_ROOT_FILENAME}",
    "corpus-spec/specs/*.md",
    "corpus-spec/specs/**/*.md",
    "corpus-spec/profiles/*.md",
    "corpus-spec/profiles/**/*.md",
    f"{LEGACY_SPEC_DIR_NAME}/{LEGACY_SPEC_ROOT_FILENAME}",
    f"{LEGACY_SPEC_DIR_NAME}/specs/*.md",
    f"{LEGACY_SPEC_DIR_NAME}/specs/**/*.md",
    f"{LEGACY_SPEC_DIR_NAME}/profiles/*.md",
    f"{LEGACY_SPEC_DIR_NAME}/profiles/**/*.md",
    f"projects/spec/code/corpus-spec/{CANONICAL_SPEC_ROOT_FILENAME}",
    f"projects/spec/code/corpus-spec/{LEGACY_SPEC_ROOT_FILENAME}",
    f"projects/spec/code/corpus-spec/{LEGACY_LOWER_SPEC_ROOT_FILENAME}",
    "projects/spec/code/corpus-spec/specs/*.md",
    "projects/spec/code/corpus-spec/specs/**/*.md",
    "projects/spec/code/corpus-spec/profiles/*.md",
    "projects/spec/code/corpus-spec/profiles/**/*.md",
    f"projects/spec/code/{LEGACY_SPEC_DIR_NAME}/{LEGACY_SPEC_ROOT_FILENAME}",
    f"projects/spec/code/{LEGACY_SPEC_DIR_NAME}/specs/*.md",
    f"projects/spec/code/{LEGACY_SPEC_DIR_NAME}/specs/**/*.md",
    f"projects/spec/code/{LEGACY_SPEC_DIR_NAME}/profiles/*.md",
    f"projects/spec/code/{LEGACY_SPEC_DIR_NAME}/profiles/**/*.md",
)

DEFAULT_EXCLUDE_PARTS = (
    ".git",
    ".catalog",
    ".corpus",
    ".venv",
    "__pycache__",
    "_archive",
    "node_modules",
)

CORPUS_IGNORE_FILENAME = ".corpusignore"

RECOMMENDED_CORPUSIGNORE_PATTERNS = (
    "projects/spec/code/corpus-catalog/",
)


class CatalogConfig(BaseModel):
    """Runtime configuration for read-only corpus catalog operations."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    corpus_root: Path
    catalog_dir: Path | None = None
    include_patterns: tuple[str, ...] = DEFAULT_INCLUDE_PATTERNS
    exclude_parts: tuple[str, ...] = DEFAULT_EXCLUDE_PARTS
    max_search_results: int = Field(default=10, ge=1, le=100)
    max_context_items: int = Field(default=12, ge=1, le=50)
    max_context_item_chars: int = Field(default=1800, ge=200, le=10000)

    @field_validator("corpus_root")
    @classmethod
    def expand_root(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("catalog_dir")
    @classmethod
    def expand_catalog_dir(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        return value.expanduser().resolve()

    @model_validator(mode="after")
    def default_catalog_dir(self) -> CatalogConfig:
        if self.catalog_dir is None:
            self.catalog_dir = self.corpus_root / ".corpus"
        return self

    def relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.corpus_root).as_posix()

    @property
    def corpus_ignore_path(self) -> Path:
        return self.corpus_root / CORPUS_IGNORE_FILENAME
