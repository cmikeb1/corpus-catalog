from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Severity = Literal["info", "warning", "error"]
SourceKind = Literal["handbook", "overview", "tasks", "registry", "readme", "spec", "note"]


class SourceRef(BaseModel):
    """Stable reference to source corpus material."""

    model_config = ConfigDict(extra="forbid")

    path: str
    kind: SourceKind = "note"
    title: str | None = None
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    excerpt: str | None = None

    @model_validator(mode="after")
    def validate_line_range(self) -> SourceRef:
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("line_end must be greater than or equal to line_start")
        return self


class CorpusItem(BaseModel):
    """Parsed corpus item with source metadata and text."""

    model_config = ConfigDict(extra="forbid")

    source: SourceRef
    title: str
    front_matter: dict[str, Any] = Field(default_factory=dict)
    text: str


class ContextItem(BaseModel):
    """Bounded source excerpt selected for a context packet."""

    model_config = ConfigDict(extra="forbid")

    source: SourceRef
    title: str
    front_matter: dict[str, Any] = Field(default_factory=dict)
    excerpt: str


class ValidationIssue(BaseModel):
    """Cheap deterministic issue found while reading the corpus."""

    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Severity
    message: str
    source: SourceRef | None = None


class CatalogQuery(BaseModel):
    """Request shape for a context packet."""

    model_config = ConfigDict(extra="forbid")

    goal: str
    cwd: str | None = None


class ContextPacket(BaseModel):
    """Source-cited context bundle for an agent or adapter."""

    model_config = ConfigDict(extra="forbid")

    query: CatalogQuery
    items: list[ContextItem]
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    guidance: list[str] = Field(default_factory=list)
