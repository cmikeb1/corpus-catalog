from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DEFAULT_INCLUDE_PATTERNS = (
    "AI.md",
    "**/AI.md",
    "corpus.md",
    "**/corpus.md",
    "**/README.md",
    "**/assets/OVERVIEW.md",
    "**/assets/epics/*/TASKS.md",
    "**/assets/epics/*/SPIKE.md",
    "**/assets/epics/*/reference/*.md",
    "**/assets/epics/*/reference/**/*.md",
    "**/assets/reference/*.md",
    "**/assets/reference/**/*.md",
    "**/registry/*.md",
    "corpus-spec/AI-SPEC.md",
    "corpus-spec/corpus-spec.md",
    "corpus-spec/specs/*.md",
    "corpus-spec/specs/**/*.md",
    "corpus-spec/profiles/*.md",
    "corpus-spec/profiles/**/*.md",
    "ai-spec/AI-SPEC.md",
    "ai-spec/specs/*.md",
    "ai-spec/specs/**/*.md",
    "ai-spec/profiles/*.md",
    "ai-spec/profiles/**/*.md",
    "projects/spec/code/corpus-spec/AI-SPEC.md",
    "projects/spec/code/corpus-spec/corpus-spec.md",
    "projects/spec/code/corpus-spec/specs/*.md",
    "projects/spec/code/corpus-spec/specs/**/*.md",
    "projects/spec/code/corpus-spec/profiles/*.md",
    "projects/spec/code/corpus-spec/profiles/**/*.md",
    "projects/spec/code/ai-spec/AI-SPEC.md",
    "projects/spec/code/ai-spec/specs/*.md",
    "projects/spec/code/ai-spec/specs/**/*.md",
    "projects/spec/code/ai-spec/profiles/*.md",
    "projects/spec/code/ai-spec/profiles/**/*.md",
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
