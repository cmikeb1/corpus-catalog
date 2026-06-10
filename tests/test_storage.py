import sqlite3
from pathlib import Path
from shutil import copytree

from corpus_catalog.config import CatalogConfig
from corpus_catalog.context import build_context_packet
from corpus_catalog.corpus import load_corpus
from corpus_catalog.projects import build_project_creation_plan
from corpus_catalog.storage import (
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
    assert manifest.corpus_identity is not None
    assert manifest.corpus_identity.corpus_uri == "corpus://cmikeb/work/brief"
    assert manifest.current_mount is not None
    assert manifest.current_mount.mount_uri == "corpus://cmikeb/work/brief@bilby"
    assert (root / ".corpus" / "AI.md").exists()
    assert (root / ".corpus" / "manifest.json").exists()
    assert (root / ".corpus" / "indexes").is_dir()
    assert (root / ".corpus" / "reports").is_dir()
    assert (root / ".corpus" / "jobs").is_dir()
    assert (root / ".corpus" / "embeddings").is_dir()
    assert not (root / ".gitignore").exists()

    status = catalog_status(config)
    assert status.state == "stale"
    assert status.next_commands == [f"catalog index --root {root}"]


def test_index_persists_inventory_validation_and_conformance(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)

    manifest = index_catalog(config)

    assert manifest.source_count == 14
    assert manifest.validation_issue_count == 0
    assert manifest.catalog_version == "0.1.0"
    assert manifest.validated_corpus_spec_version == "v0.19"
    assert manifest.ai_spec_baseline == "v0.18"
    assert manifest.corpus_identity is not None
    assert manifest.corpus_identity.corpus_uri == "corpus://cmikeb/work/brief"
    assert manifest.corpus_identity.aliases == ["work/brief", "cmikeb/work/brief"]
    assert manifest.current_mount is not None
    assert manifest.current_mount.mount_uri == "corpus://cmikeb/work/brief@bilby"
    assert manifest.current_mount.aliases == [
        "work/brief",
        "cmikeb/work/brief",
        "work/brief@bilby",
        "cmikeb/work/brief@bilby",
    ]
    assert {module.path: module.module_type for module in manifest.spec_modules} == {
        "corpus-spec/AI-SPEC.md": "root-spec",
        "corpus-spec/profiles/human-workspace.md": "profile",
        "corpus-spec/profiles/initiatives.md": "profile",
        "corpus-spec/profiles/project.md": "profile",
        "corpus-spec/profiles/reference.md": "profile",
        "corpus-spec/specs/corpus-identity.md": "spec",
        "corpus-spec/specs/profile-composition.md": "spec",
        "corpus-spec/specs/tooling-and-validation.md": "spec",
    }
    assert {module.path: module.module_id for module in manifest.spec_modules} == {
        "corpus-spec/AI-SPEC.md": "root",
        "corpus-spec/profiles/human-workspace.md": "human-workspace",
        "corpus-spec/profiles/initiatives.md": "initiatives",
        "corpus-spec/profiles/project.md": "project",
        "corpus-spec/profiles/reference.md": "reference",
        "corpus-spec/specs/corpus-identity.md": "corpus-identity",
        "corpus-spec/specs/profile-composition.md": "profile-composition",
        "corpus-spec/specs/tooling-and-validation.md": "tooling-and-validation",
    }
    assert {marker.path for marker in manifest.conformance} == {
        "AI.md",
        "corpus-spec/AI-SPEC.md",
        "corpus-spec/profiles/human-workspace.md",
        "corpus-spec/profiles/initiatives.md",
        "corpus-spec/profiles/project.md",
        "corpus-spec/profiles/reference.md",
        "corpus-spec/specs/corpus-identity.md",
        "corpus-spec/specs/profile-composition.md",
        "corpus-spec/specs/tooling-and-validation.md",
        "projects/demo/AI.md",
    }
    assert {
        marker.path: marker.ai_spec_version for marker in manifest.conformance
    } == {
        "AI.md": "v0.18",
        "corpus-spec/AI-SPEC.md": "v0.18",
        "corpus-spec/profiles/human-workspace.md": "v0.18",
        "corpus-spec/profiles/initiatives.md": "v0.18",
        "corpus-spec/profiles/project.md": "v0.18",
        "corpus-spec/profiles/reference.md": "v0.18",
        "corpus-spec/specs/corpus-identity.md": "v0.18",
        "corpus-spec/specs/profile-composition.md": "v0.18",
        "corpus-spec/specs/tooling-and-validation.md": "v0.18",
        "projects/demo/AI.md": "v0.16",
    }

    assert (root / ".corpus" / "indexes" / "sources.jsonl").exists()
    assert (root / ".corpus" / "indexes" / "validation-issues.jsonl").exists()
    assert (root / ".corpus" / "reports" / "validation.md").exists()
    assert (root / ".corpus" / "jobs" / "last-run.json").exists()

    with sqlite3.connect(root / ".corpus" / "catalog.sqlite") as connection:
        source_count = connection.execute("select count(*) from sources").fetchone()[0]
        issue_count = connection.execute(
            "select count(*) from validation_issues"
        ).fetchone()[0]
        marker_count = connection.execute(
            "select count(*) from conformance_markers"
        ).fetchone()[0]
        spec_module_rows = connection.execute(
            """
            select path, module_type, module_id, status, source_checkout
            from spec_modules
            order by path
            """
        ).fetchall()
        identity_rows = connection.execute(
            """
            select corpus_uri, owner_id, realm, tier, aliases_json
            from corpus_identity
            """
        ).fetchall()
        mount_rows = connection.execute(
            """
            select
              mount_uri,
              corpus_uri,
              owner_id,
              realm,
              tier,
              node_id,
              sync_transport,
              root_path,
              aliases_json
            from corpus_mounts
            """
        ).fetchall()

    assert source_count == 14
    assert issue_count == 0
    assert marker_count == 10
    assert spec_module_rows == [
        ("corpus-spec/AI-SPEC.md", "root-spec", "root", None, "tier-root"),
        (
            "corpus-spec/profiles/human-workspace.md",
            "profile",
            "human-workspace",
            "stable",
            "tier-root",
        ),
        (
            "corpus-spec/profiles/initiatives.md",
            "profile",
            "initiatives",
            "beta",
            "tier-root",
        ),
        ("corpus-spec/profiles/project.md", "profile", "project", "stable", "tier-root"),
        ("corpus-spec/profiles/reference.md", "profile", "reference", "stable", "tier-root"),
        (
            "corpus-spec/specs/corpus-identity.md",
            "spec",
            "corpus-identity",
            "stable",
            "tier-root",
        ),
        (
            "corpus-spec/specs/profile-composition.md",
            "spec",
            "profile-composition",
            "stable",
            "tier-root",
        ),
        (
            "corpus-spec/specs/tooling-and-validation.md",
            "spec",
            "tooling-and-validation",
            "stable",
            "tier-root",
        ),
    ]
    assert identity_rows == [
        (
            "corpus://cmikeb/work/brief",
            "cmikeb",
            "work",
            "BRIEF",
            '["work/brief", "cmikeb/work/brief"]',
        )
    ]
    assert mount_rows == [
        (
            "corpus://cmikeb/work/brief@bilby",
            "corpus://cmikeb/work/brief",
            "cmikeb",
            "work",
            "BRIEF",
            "bilby",
            "git",
            str(root.resolve()),
            (
                '["work/brief", "cmikeb/work/brief", '
                '"work/brief@bilby", "cmikeb/work/brief@bilby"]'
            ),
        )
    ]
    assert catalog_status(config).state == "fresh"


def test_default_source_scope_includes_spike_and_epic_reference(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)

    paths = {item.source.path for item in load_corpus(config)}

    assert "projects/demo/assets/epics/001-DEMO/SPIKE.md" in paths
    assert "projects/demo/assets/epics/001-DEMO/reference/demo-candidate.md" in paths


def test_spec_and_profile_modules_are_first_class_sources(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)

    items = {item.source.path: item for item in load_corpus(config)}

    assert items["corpus-spec/AI-SPEC.md"].source.kind == "spec-root"
    assert items["corpus-spec/specs/profile-composition.md"].source.kind == "spec-module"
    assert items["corpus-spec/profiles/project.md"].source.kind == "profile-module"


def test_corpusignore_excludes_package_local_code_markdown(tmp_path):
    root = copy_fixture(tmp_path)
    code_readme = root / "projects" / "spec" / "code" / "catalog" / "README.md"
    code_readme.parent.mkdir(parents=True)
    code_readme.write_text("# Package README\n", encoding="utf-8")
    (root / ".corpusignore").write_text(
        "projects/spec/code/corpus-catalog/\n",
        encoding="utf-8",
    )
    config = CatalogConfig(corpus_root=root)

    paths = {item.source.path for item in load_corpus(config)}

    assert "projects/spec/code/corpus-catalog/README.md" not in paths


def test_corpusignore_excludes_single_file_pattern(tmp_path):
    root = copy_fixture(tmp_path)
    ignored_path = "projects/demo/assets/epics/001-DEMO/reference/demo-candidate.md"
    (root / ".corpusignore").write_text(f"{ignored_path}\n", encoding="utf-8")
    config = CatalogConfig(corpus_root=root)

    paths = {item.source.path for item in load_corpus(config)}

    assert ignored_path not in paths


def test_corpus_outputs_are_excluded_from_source_discovery(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)

    index_catalog(config)

    paths = {item.source.path for item in load_corpus(config)}
    assert ".corpus/AI.md" not in paths
    assert all(not path.startswith(".corpus/") for path in paths)


def test_legacy_catalog_outputs_are_excluded_from_source_discovery(tmp_path):
    root = copy_fixture(tmp_path)
    legacy_ai = root / ".catalog" / "AI.md"
    legacy_ai.parent.mkdir()
    legacy_ai.write_text("# Legacy generated state\n", encoding="utf-8")
    config = CatalogConfig(corpus_root=root)

    paths = {item.source.path for item in load_corpus(config)}

    assert ".catalog/AI.md" not in paths
    assert all(not path.startswith(".catalog/") for path in paths)


def test_status_reports_legacy_catalog_state_without_reading_it(tmp_path):
    root = copy_fixture(tmp_path)
    legacy_manifest = root / ".catalog" / "manifest.json"
    legacy_manifest.parent.mkdir()
    legacy_manifest.write_text("{}\n", encoding="utf-8")
    config = CatalogConfig(corpus_root=root)

    status = catalog_status(config)

    assert status.state == "missing"
    assert status.catalog_dir == str(root.resolve() / ".corpus")
    assert status.stale_reasons == [
        ".corpus has not been initialized.",
        "Legacy .catalog generated state exists but is no longer read; "
        "run catalog index and delete .catalog after validation.",
    ]


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
    assert plan.commands == [
        'catalog context --cwd projects/garden-tools --goal "Create project Garden Tools"',
        "catalog validate --format json",
        "catalog index",
    ]
    assert f"Run suggested commands from the corpus root: {root.resolve()}." in plan.notes
