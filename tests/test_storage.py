import sqlite3
from pathlib import Path
from shutil import copytree

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.context import build_context_packet
from ai_spec_catalog.corpus import load_corpus
from ai_spec_catalog.projects import build_project_creation_plan
from ai_spec_catalog.storage import (
    catalog_status,
    index_catalog,
    init_catalog,
    load_fresh_indexed_corpus,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_brief"


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "mini_brief"
    copytree(FIXTURE_ROOT, root)
    return root


def test_init_creates_catalog_workbench_without_source_edits(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)

    manifest = init_catalog(config)

    assert manifest.source_count == 0
    assert (root / ".catalog" / "AI.md").exists()
    assert (root / ".catalog" / "manifest.json").exists()
    assert (root / ".catalog" / "indexes").is_dir()
    assert (root / ".catalog" / "reports").is_dir()
    assert (root / ".catalog" / "jobs").is_dir()
    assert (root / ".catalog" / "embeddings").is_dir()
    assert not (root / ".gitignore").exists()

    status = catalog_status(config)
    assert status.state == "stale"
    assert status.next_commands == [f"catalog index --root {root}"]


def test_index_persists_inventory_validation_and_conformance(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)

    manifest = index_catalog(config)

    assert manifest.source_count == 4
    assert manifest.validation_issue_count == 0
    assert manifest.ai_spec_baseline == "v0.18"
    assert {marker.path for marker in manifest.conformance} == {
        "AI.md",
        "projects/demo/AI.md",
    }
    assert {
        marker.path: marker.ai_spec_version for marker in manifest.conformance
    } == {
        "AI.md": "v0.18",
        "projects/demo/AI.md": "v0.16",
    }

    assert (root / ".catalog" / "indexes" / "sources.jsonl").exists()
    assert (root / ".catalog" / "indexes" / "validation-issues.jsonl").exists()
    assert (root / ".catalog" / "reports" / "validation.md").exists()
    assert (root / ".catalog" / "jobs" / "last-run.json").exists()

    with sqlite3.connect(root / ".catalog" / "catalog.sqlite") as connection:
        source_count = connection.execute("select count(*) from sources").fetchone()[0]
        issue_count = connection.execute(
            "select count(*) from validation_issues"
        ).fetchone()[0]
        marker_count = connection.execute(
            "select count(*) from conformance_markers"
        ).fetchone()[0]

    assert source_count == 4
    assert issue_count == 0
    assert marker_count == 2
    assert catalog_status(config).state == "fresh"


def test_catalog_outputs_are_excluded_from_source_discovery(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)

    index_catalog(config)

    paths = {item.source.path for item in load_corpus(config)}
    assert ".catalog/AI.md" not in paths
    assert all(not path.startswith(".catalog/") for path in paths)


def test_status_uses_content_hash_for_staleness(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)
    index_catalog(config)

    handbook = root / "projects" / "demo" / "AI.md"
    handbook.write_text(
        handbook.read_text(encoding="utf-8") + "\nAdditional guidance.\n",
        encoding="utf-8",
    )

    status = catalog_status(config)

    assert status.state == "stale"
    assert "Source content fingerprint changed since last index." in status.stale_reasons


def test_context_packet_uses_fresh_index_metadata(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)
    manifest = index_catalog(config)

    indexed_items = load_fresh_indexed_corpus(config)
    packet = build_context_packet(
        goal="Create a project according to the local AI-SPEC baseline",
        cwd="projects/demo",
        config=config,
    )

    assert indexed_items is not None
    assert packet.baseline == "v0.18"
    assert packet.source_fingerprint == manifest.source_fingerprint
    assert "AI.md" in {item.source.path for item in packet.items}


def test_project_creation_plan_is_read_only_and_source_cited(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)
    index_catalog(config)

    plan = build_project_creation_plan(
        name="Garden Tools",
        slug="garden-tools",
        tag="personal",
        tier="BRIEF",
        config=config,
    )

    assert plan.project_path == "projects/garden-tools"
    assert plan.ai_spec_baseline == "v0.18"
    assert plan.tag == "personal"
    assert plan.tier == "BRIEF"
    assert not plan.warnings
    assert "AI.md" in {source.path for source in plan.sources}
    assert {file.path for file in plan.files} >= {
        "projects/garden-tools/AI.md",
        "projects/garden-tools/assets/OVERVIEW.md",
        "projects/garden-tools/assets/epics/001-BOOTSTRAP/SPIKE.md",
        "projects/garden-tools/assets/epics/001-BOOTSTRAP/TASKS.md",
        "AI.md",
    }
    assert all(command.startswith("catalog ") for command in plan.commands)
