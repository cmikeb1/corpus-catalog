from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.corpus import load_corpus, source_fingerprint
from ai_spec_catalog.models import (
    CatalogArtifact,
    CatalogManifest,
    CatalogStatus,
    ConformanceMarker,
    CorpusItem,
    SourceRef,
    SpecModule,
    ValidationIssue,
)
from ai_spec_catalog.validators import validate_corpus


CATALOG_SCHEMA_VERSION = 1
CATALOG_DIRS = ("indexes", "reports", "jobs", "embeddings")
REQUIRED_ARTIFACTS = (
    ("AI.md", "ai-readme"),
    ("manifest.json", "manifest"),
    ("catalog.sqlite", "sqlite"),
    ("indexes/sources.jsonl", "jsonl"),
    ("indexes/validation-issues.jsonl", "jsonl"),
    ("reports/validation.md", "report"),
    ("jobs/last-run.json", "job"),
)


def init_catalog(config: CatalogConfig) -> CatalogManifest:
    """Create the generated .corpus workbench without indexing sources."""

    ensure_catalog_dirs(config)
    manifest = CatalogManifest(
        schema_version=CATALOG_SCHEMA_VERSION,
        catalog_version=catalog_version(),
        corpus_root=str(config.corpus_root),
        catalog_dir=str(config.catalog_dir),
        generated_at=utc_now(),
        artifacts=current_artifacts(config),
    )
    write_manifest(config, manifest)
    write_catalog_ai(config, manifest)
    manifest.artifacts = current_artifacts(config)
    write_manifest(config, manifest)
    write_catalog_ai(config, manifest)
    return manifest


def index_catalog(config: CatalogConfig) -> CatalogManifest:
    """Build and persist the source inventory, validations, and manifest."""

    ensure_catalog_dirs(config)
    indexed_at = utc_now()
    items = load_corpus(config)
    markers = extract_conformance_markers(items)
    spec_modules = extract_spec_modules(items)
    baseline = select_ai_spec_baseline(markers)
    issues = validate_corpus(items, config)
    fingerprint = source_fingerprint(items)

    write_sources_jsonl(config, items)
    write_validation_jsonl(config, issues)
    write_validation_report(config, issues, baseline, fingerprint, indexed_at)
    write_sqlite(config, items, issues, markers, spec_modules, indexed_at)
    write_last_run(config, items, issues, fingerprint, indexed_at)

    manifest = CatalogManifest(
        schema_version=CATALOG_SCHEMA_VERSION,
        catalog_version=catalog_version(),
        corpus_root=str(config.corpus_root),
        catalog_dir=str(config.catalog_dir),
        generated_at=indexed_at,
        ai_spec_baseline=baseline,
        source_fingerprint=fingerprint,
        source_count=len(items),
        validation_issue_count=len(issues),
        artifacts=current_artifacts(config),
        conformance=markers,
        spec_modules=spec_modules,
    )
    write_manifest(config, manifest)
    write_catalog_ai(config, manifest)
    manifest.artifacts = current_artifacts(config)
    write_manifest(config, manifest)
    return manifest


def catalog_status(config: CatalogConfig) -> CatalogStatus:
    manifest = read_manifest(config)
    manifest_exists = manifest is not None
    missing_artifacts = [
        rel_path
        for rel_path, _kind in REQUIRED_ARTIFACTS
        if not (config.catalog_dir / rel_path).exists()
    ]

    if not config.catalog_dir.exists() or not manifest_exists:
        stale_reasons = [".corpus has not been initialized."]
        legacy_dir = config.corpus_root / ".catalog"
        if legacy_dir.exists():
            stale_reasons.append(
                "Legacy .catalog generated state exists but is no longer read; "
                "run catalog index and delete .catalog after validation."
            )
        return CatalogStatus(
            state="missing",
            corpus_root=str(config.corpus_root),
            catalog_dir=str(config.catalog_dir),
            manifest_exists=manifest_exists,
            missing_artifacts=missing_artifacts,
            stale_reasons=stale_reasons,
            next_commands=[f"catalog init --root {config.corpus_root}"],
            manifest=manifest,
        )

    stale_reasons: list[str] = []
    if missing_artifacts:
        stale_reasons.append("One or more required .corpus artifacts are missing.")

    try:
        current_items = load_corpus(config)
    except OSError as error:
        stale_reasons.append(f"Could not scan source corpus: {error}")
        current_fingerprint = None
    else:
        current_fingerprint = source_fingerprint(current_items)
        if manifest.source_fingerprint != current_fingerprint:
            stale_reasons.append("Source content fingerprint changed since last index.")

    state = "fresh" if not stale_reasons else "stale"
    next_commands = [] if state == "fresh" else [f"catalog index --root {config.corpus_root}"]

    return CatalogStatus(
        state=state,
        corpus_root=str(config.corpus_root),
        catalog_dir=str(config.catalog_dir),
        manifest_exists=manifest_exists,
        missing_artifacts=missing_artifacts,
        stale_reasons=stale_reasons,
        next_commands=next_commands,
        manifest=manifest,
    )


def load_fresh_indexed_corpus(config: CatalogConfig) -> list[CorpusItem] | None:
    status = catalog_status(config)
    if status.state != "fresh":
        return None

    sqlite_path = config.catalog_dir / "catalog.sqlite"
    if not sqlite_path.exists():
        return None

    with sqlite3.connect(sqlite_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            select
              path,
              kind,
              title,
              front_matter_json,
              line_start,
              line_end,
              excerpt,
              text,
              content_hash
            from sources
            order by path
            """
        ).fetchall()

    return [
        CorpusItem(
            source=SourceRef(
                path=row["path"],
                kind=row["kind"],
                title=row["title"],
                line_start=row["line_start"],
                line_end=row["line_end"],
                excerpt=row["excerpt"],
            ),
            title=row["title"] or row["path"],
            front_matter=json.loads(row["front_matter_json"] or "{}"),
            text=row["text"] or "",
            content_hash=row["content_hash"],
        )
        for row in rows
    ]


def load_index_or_corpus(config: CatalogConfig) -> list[CorpusItem]:
    return load_fresh_indexed_corpus(config) or load_corpus(config)


def read_manifest(config: CatalogConfig) -> CatalogManifest | None:
    path = config.catalog_dir / "manifest.json"
    if not path.exists():
        return None
    return CatalogManifest.model_validate_json(path.read_text(encoding="utf-8"))


def write_manifest(config: CatalogConfig, manifest: CatalogManifest) -> None:
    write_json(config.catalog_dir / "manifest.json", manifest.model_dump(mode="json"))


def ensure_catalog_dirs(config: CatalogConfig) -> None:
    config.catalog_dir.mkdir(parents=True, exist_ok=True)
    for dirname in CATALOG_DIRS:
        (config.catalog_dir / dirname).mkdir(parents=True, exist_ok=True)


def write_sources_jsonl(config: CatalogConfig, items: list[CorpusItem]) -> None:
    rows = [item.model_dump(mode="json") for item in items]
    write_jsonl(config.catalog_dir / "indexes" / "sources.jsonl", rows)


def write_validation_jsonl(
    config: CatalogConfig, issues: list[ValidationIssue]
) -> None:
    rows = [issue.model_dump(mode="json") for issue in issues]
    write_jsonl(config.catalog_dir / "indexes" / "validation-issues.jsonl", rows)


def write_last_run(
    config: CatalogConfig,
    items: list[CorpusItem],
    issues: list[ValidationIssue],
    fingerprint: str,
    indexed_at: str,
) -> None:
    write_json(
        config.catalog_dir / "jobs" / "last-run.json",
        {
            "command": "catalog index",
            "indexed_at": indexed_at,
            "source_count": len(items),
            "validation_issue_count": len(issues),
            "source_fingerprint": fingerprint,
        },
    )


def write_sqlite(
    config: CatalogConfig,
    items: list[CorpusItem],
    issues: list[ValidationIssue],
    markers: list[ConformanceMarker],
    spec_modules: list[SpecModule],
    indexed_at: str,
) -> None:
    sqlite_path = config.catalog_dir / "catalog.sqlite"
    with sqlite3.connect(sqlite_path) as connection:
        connection.executescript(
            """
            create table if not exists sources (
              path text primary key,
              kind text not null,
              title text,
              front_matter_json text not null,
              line_start integer,
              line_end integer,
              excerpt text,
              text text not null,
              content_hash text,
              indexed_at text not null
            );

            create table if not exists validation_issues (
              id integer primary key autoincrement,
              code text not null,
              severity text not null,
              message text not null,
              baseline text,
              source_path text,
              source_kind text,
              source_title text,
              source_line_start integer,
              source_line_end integer,
              source_excerpt text,
              indexed_at text not null
            );

            create table if not exists conformance_markers (
              path text primary key,
              ai_spec_version text,
              ai_spec_profile text,
              ai_spec_adoption text,
              ai_spec_reviewed text,
              ai_spec_betas_json text not null,
              indexed_at text not null
            );

            create table if not exists spec_modules (
              path text primary key,
              module_type text not null,
              module_id text not null,
              title text,
              doc_type text,
              status text,
              ai_spec_version text,
              source_checkout text,
              indexed_at text not null
            );

            delete from sources;
            delete from validation_issues;
            delete from conformance_markers;
            delete from spec_modules;
            """
        )
        connection.executemany(
            """
            insert into sources (
              path,
              kind,
              title,
              front_matter_json,
              line_start,
              line_end,
              excerpt,
              text,
              content_hash,
              indexed_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.source.path,
                    item.source.kind,
                    item.title,
                    json.dumps(item.front_matter, sort_keys=True),
                    item.source.line_start,
                    item.source.line_end,
                    item.source.excerpt,
                    item.text,
                    item.content_hash,
                    indexed_at,
                )
                for item in items
            ],
        )
        connection.executemany(
            """
            insert into validation_issues (
              code,
              severity,
              message,
              baseline,
              source_path,
              source_kind,
              source_title,
              source_line_start,
              source_line_end,
              source_excerpt,
              indexed_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    issue.code,
                    issue.severity,
                    issue.message,
                    issue.baseline,
                    issue.source.path if issue.source else None,
                    issue.source.kind if issue.source else None,
                    issue.source.title if issue.source else None,
                    issue.source.line_start if issue.source else None,
                    issue.source.line_end if issue.source else None,
                    issue.source.excerpt if issue.source else None,
                    indexed_at,
                )
                for issue in issues
            ],
        )
        connection.executemany(
            """
            insert into conformance_markers (
              path,
              ai_spec_version,
              ai_spec_profile,
              ai_spec_adoption,
              ai_spec_reviewed,
              ai_spec_betas_json,
              indexed_at
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    marker.path,
                    marker.ai_spec_version,
                    marker.ai_spec_profile,
                    marker.ai_spec_adoption,
                    marker.ai_spec_reviewed,
                    json.dumps(marker.ai_spec_betas, sort_keys=True),
                    indexed_at,
                )
                for marker in markers
            ],
        )
        connection.executemany(
            """
            insert into spec_modules (
              path,
              module_type,
              module_id,
              title,
              doc_type,
              status,
              ai_spec_version,
              source_checkout,
              indexed_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    module.path,
                    module.module_type,
                    module.module_id,
                    module.title,
                    module.doc_type,
                    module.status,
                    module.ai_spec_version,
                    module.source_checkout,
                    indexed_at,
                )
                for module in spec_modules
            ],
        )
        try_create_fts(connection, items)


def try_create_fts(connection: sqlite3.Connection, items: list[CorpusItem]) -> None:
    try:
        connection.execute(
            """
            create virtual table if not exists sources_fts using fts5(
              path,
              title,
              front_matter,
              text
            )
            """
        )
    except sqlite3.OperationalError:
        return

    connection.execute("delete from sources_fts")
    connection.executemany(
        """
        insert into sources_fts (path, title, front_matter, text)
        values (?, ?, ?, ?)
        """,
        [
            (
                item.source.path,
                item.title,
                json.dumps(item.front_matter, sort_keys=True),
                item.text,
            )
            for item in items
        ],
    )


def write_validation_report(
    config: CatalogConfig,
    issues: list[ValidationIssue],
    baseline: str | None,
    fingerprint: str,
    generated_at: str,
) -> None:
    lines = [
        "# Catalog Validation Report",
        "",
        f"Generated: {generated_at}",
        f"Corpus root: `{config.corpus_root}`",
        f"AI-SPEC baseline: `{baseline or 'unknown'}`",
        f"Source fingerprint: `{fingerprint}`",
        f"Issue count: {len(issues)}",
        "",
    ]
    if not issues:
        lines.extend(["No validation issues found.", ""])
    else:
        lines.extend(["## Issues", ""])
        for issue in issues:
            source_path = issue.source.path if issue.source else "corpus"
            lines.append(
                f"- **{issue.severity}** `{issue.code}`: {issue.message} "
                f"Source: `{source_path}`. Baseline: `{issue.baseline or baseline or 'unknown'}`."
            )
        lines.append("")

    (config.catalog_dir / "reports" / "validation.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_catalog_ai(config: CatalogConfig, manifest: CatalogManifest) -> None:
    status_command = f"catalog status --root {config.corpus_root}"
    index_command = f"catalog index --root {config.corpus_root}"
    lines = [
        "---",
        'title: "AI.md - Corpus Derived State"',
        "doc_type: ai-entry",
        "generated_by: catalog",
        "---",
        "",
        "# AI.md - Corpus Derived State",
        "",
        "This `.corpus/` directory is generated by Catalog. "
        "Treat source corpus files as canonical.",
        "",
        "## What Lives Here",
        "",
        "- `manifest.json` records freshness, source fingerprint, artifacts, "
        "conformance markers, and spec/profile module inventory.",
        "- `catalog.sqlite` is the durable local query surface.",
        "- `indexes/*.jsonl` are portable machine-readable exports.",
        "- `reports/validation.md` is the human validation receipt.",
        "- `embeddings/` is reserved for future vector artifacts.",
        "",
        "## Freshness",
        "",
        f"- Generated: `{manifest.generated_at or 'not indexed'}`",
        f"- AI-SPEC baseline: `{manifest.ai_spec_baseline or 'unknown'}`",
        f"- Source count: `{manifest.source_count}`",
        f"- Spec/profile modules: `{len(manifest.spec_modules)}`",
        f"- Validation issues: `{manifest.validation_issue_count}`",
        "",
        "## Commands",
        "",
        f"- Check status: `{status_command}`",
        f"- Refresh derived state: `{index_command}`",
        "",
        "Do not edit these files by hand; rerun Catalog instead.",
        "",
    ]
    (config.catalog_dir / "AI.md").write_text("\n".join(lines), encoding="utf-8")


def extract_conformance_markers(items: list[CorpusItem]) -> list[ConformanceMarker]:
    markers: list[ConformanceMarker] = []
    for item in items:
        front_matter = item.front_matter
        if not any(key.startswith("ai_spec_") for key in front_matter):
            continue

        markers.append(
            ConformanceMarker(
                path=item.source.path,
                ai_spec_version=string_or_none(front_matter.get("ai_spec_version")),
                ai_spec_profile=string_or_none(front_matter.get("ai_spec_profile")),
                ai_spec_adoption=string_or_none(front_matter.get("ai_spec_adoption")),
                ai_spec_reviewed=string_or_none(front_matter.get("ai_spec_reviewed")),
                ai_spec_betas=list_of_strings(front_matter.get("ai_spec_betas")),
            )
        )
    return sorted(markers, key=lambda marker: marker.path)


def extract_spec_modules(items: list[CorpusItem]) -> list[SpecModule]:
    modules: list[SpecModule] = []
    for item in items:
        module_type = spec_module_type(item)
        if module_type is None:
            continue

        modules.append(
            SpecModule(
                path=item.source.path,
                module_type=module_type,
                module_id=spec_module_id(item, module_type),
                title=item.title,
                doc_type=string_or_none(item.front_matter.get("doc_type")),
                status=string_or_none(item.front_matter.get("ai_spec_status")),
                ai_spec_version=string_or_none(item.front_matter.get("ai_spec_version")),
                source_checkout=spec_source_checkout(item.source.path),
            )
        )
    return sorted(modules, key=lambda module: module.path)


def spec_module_type(item: CorpusItem):
    if item.source.kind == "spec-root":
        return "root-spec"
    if item.source.kind == "spec-module":
        return "spec"
    if item.source.kind == "profile-module":
        return "profile"
    return None


def spec_module_id(item: CorpusItem, module_type: str) -> str:
    if module_type == "spec":
        value = item.front_matter.get("ai_spec_spec_id")
    elif module_type == "profile":
        value = item.front_matter.get("ai_spec_profile_id")
    else:
        value = "root"

    if value:
        return str(value)
    return Path(item.source.path).stem


def spec_source_checkout(path: str) -> str | None:
    if path.startswith(("projects/spec/code/ai-spec/", "projects/spec/code/corpus-spec/")):
        return "source-checkout"
    if path.startswith(("ai-spec/", "corpus-spec/")):
        return "tier-root"
    return None


def select_ai_spec_baseline(markers: list[ConformanceMarker]) -> str | None:
    root_marker = next((marker for marker in markers if marker.path == "AI.md"), None)
    if root_marker and root_marker.ai_spec_version:
        return root_marker.ai_spec_version

    for marker in markers:
        if marker.ai_spec_version:
            return marker.ai_spec_version
    return None


def current_artifacts(config: CatalogConfig) -> list[CatalogArtifact]:
    artifacts: list[CatalogArtifact] = []
    for rel_path, kind in REQUIRED_ARTIFACTS:
        path = config.catalog_dir / rel_path
        artifacts.append(
            CatalogArtifact(
                path=f".corpus/{rel_path}",
                kind=kind,
                exists=path.exists(),
                updated_at=mtime_iso(path) if path.exists() else None,
            )
        )
    for dirname in CATALOG_DIRS:
        path = config.catalog_dir / dirname
        artifacts.append(
            CatalogArtifact(
                path=f".corpus/{dirname}/",
                kind="directory",
                exists=path.exists(),
                updated_at=mtime_iso(path) if path.exists() else None,
            )
        )
    return artifacts


def catalog_version() -> str:
    try:
        return version("ai-spec-catalog")
    except PackageNotFoundError:
        return "0.1.0"


def gitignore_warning(config: CatalogConfig) -> str | None:
    gitignore = config.corpus_root / ".gitignore"
    if not gitignore.exists():
        return "Catalog did not edit .gitignore; consider ignoring .corpus/."

    patterns = {
        line.strip().rstrip("/")
        for line in gitignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if ".corpus" not in patterns:
        return "Catalog did not edit .gitignore; consider ignoring .corpus/."
    return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(
        microsecond=0
    ).isoformat()


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def list_of_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
