from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Severity = Literal["info", "warning", "error"]
SourceKind = Literal[
    "handbook",
    "overview",
    "tasks",
    "spike",
    "reference",
    "registry",
    "readme",
    "spec-root",
    "spec-module",
    "profile-module",
    "spec",
    "note",
]
CatalogState = Literal["missing", "stale", "fresh"]
SpecModuleType = Literal["root-spec", "spec", "profile"]
SyncConfidence = Literal["git", "local-metadata", "declared-only"]


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
    content_hash: str | None = None


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
    baseline: str | None = None


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
    baseline: str | None = None
    source_fingerprint: str | None = None


class ConformanceMarker(BaseModel):
    """Declared AI-SPEC conformance metadata discovered in source files."""

    model_config = ConfigDict(extra="forbid")

    path: str
    ai_spec_version: str | None = None
    ai_spec_profile: str | None = None
    ai_spec_adoption: str | None = None
    ai_spec_reviewed: str | None = None
    ai_spec_betas: list[str] = Field(default_factory=list)


class SpecModule(BaseModel):
    """AI-SPEC root/spec/profile module discovered in source."""

    model_config = ConfigDict(extra="forbid")

    path: str
    module_type: SpecModuleType
    module_id: str
    title: str | None = None
    doc_type: str | None = None
    status: str | None = None
    ai_spec_version: str | None = None
    source_checkout: str | None = None


class CorpusIdentity(BaseModel):
    """Logical AI-SPEC corpus identity declared by a corpus root."""

    model_config = ConfigDict(extra="forbid")

    corpus_uri: str
    owner_id: str
    realm: str
    tier: str
    aliases: list[str] = Field(default_factory=list)


class CorpusMount(BaseModel):
    """One local mount of a logical corpus on a node."""

    model_config = ConfigDict(extra="forbid")

    corpus_uri: str
    mount_uri: str
    owner_id: str
    realm: str
    tier: str
    node_id: str
    sync_transport: str | None = None
    root_path: str
    aliases: list[str] = Field(default_factory=list)


class KnownCorpusMount(CorpusMount):
    """A mount recorded in the per-user corpus registry."""

    registered_at: str | None = None
    last_seen_at: str | None = None


class MountSyncStatus(BaseModel):
    """Realm-specific local freshness signal, separate from validation."""

    model_config = ConfigDict(extra="forbid")

    realm: str
    sync_transport: str | None = None
    confidence: SyncConfidence
    state: str
    detail: str
    branch: str | None = None
    commit: str | None = None
    dirty_paths: int | None = None


class MountInventory(BaseModel):
    """Current and known corpus mounts visible to Catalog."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    registry_path: str
    current_mount: CorpusMount | None = None
    known_mounts: list[KnownCorpusMount] = Field(default_factory=list)
    registry_updated: bool = False
    sync_status: MountSyncStatus | None = None


class CatalogArtifact(BaseModel):
    """Generated artifact tracked in the Catalog manifest."""

    model_config = ConfigDict(extra="forbid")

    path: str
    kind: str
    exists: bool = False
    updated_at: str | None = None


class CatalogManifest(BaseModel):
    """Manifest for the generated .corpus workbench."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    catalog_version: str
    corpus_root: str
    catalog_dir: str
    generated_at: str | None = None
    ai_spec_baseline: str | None = None
    source_fingerprint: str | None = None
    source_count: int = 0
    validation_issue_count: int = 0
    corpus_identity: CorpusIdentity | None = None
    current_mount: CorpusMount | None = None
    artifacts: list[CatalogArtifact] = Field(default_factory=list)
    conformance: list[ConformanceMarker] = Field(default_factory=list)
    spec_modules: list[SpecModule] = Field(default_factory=list)


class CatalogStatus(BaseModel):
    """Freshness and availability report for .corpus derived state."""

    model_config = ConfigDict(extra="forbid")

    state: CatalogState
    corpus_root: str
    catalog_dir: str
    manifest_exists: bool
    missing_artifacts: list[str] = Field(default_factory=list)
    stale_reasons: list[str] = Field(default_factory=list)
    next_commands: list[str] = Field(default_factory=list)
    current_mount: CorpusMount | None = None
    mount_sync_status: MountSyncStatus | None = None
    manifest: CatalogManifest | None = None


class ProjectPlanFile(BaseModel):
    """One file operation in a read-only project scaffold plan."""

    model_config = ConfigDict(extra="forbid")

    path: str
    action: Literal["create", "update", "inspect"]
    purpose: str
    required: bool = True


class ProjectCreationPlan(BaseModel):
    """Dry-run contract for creating an AI-SPEC-shaped project."""

    model_config = ConfigDict(extra="forbid")

    name: str
    slug: str
    project_path: str
    lifecycle: str
    tag: str | None = None
    tier: str | None = None
    ai_spec_baseline: str | None = None
    files: list[ProjectPlanFile]
    sources: list[SourceRef]
    commands: list[str]
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
