from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


DEFAULT_INCLUDE_PATTERNS = (
    "AI.md",
    "**/AI.md",
    "**/README.md",
    "**/assets/OVERVIEW.md",
    "**/assets/epics/*/TASKS.md",
    "**/registry/*.md",
    "ai-spec/AI-SPEC.md",
    "ai-spec/profiles/**/*.md",
)

DEFAULT_EXCLUDE_PARTS = (
    ".git",
    ".venv",
    "__pycache__",
    "_archive",
    "node_modules",
)


class CatalogConfig(BaseModel):
    """Runtime configuration for read-only corpus catalog operations."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    corpus_root: Path
    include_patterns: tuple[str, ...] = DEFAULT_INCLUDE_PATTERNS
    exclude_parts: tuple[str, ...] = DEFAULT_EXCLUDE_PARTS
    max_search_results: int = Field(default=10, ge=1, le=100)
    max_context_items: int = Field(default=12, ge=1, le=50)
    max_context_item_chars: int = Field(default=1800, ge=200, le=10000)

    @field_validator("corpus_root")
    @classmethod
    def expand_root(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    def relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.corpus_root).as_posix()
