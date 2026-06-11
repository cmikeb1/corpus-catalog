from pathlib import Path
from shutil import copytree

import pytest

from corpus_catalog.config import CatalogConfig
from corpus_catalog.corpus import load_corpus
from corpus_catalog.identity import (
    CorpusIdentityError,
    build_mount_inventory,
    extract_current_mount,
    resolve_current_mount_selector,
)
from corpus_catalog.naming import LEGACY_ENTRY_DOC_TYPE, LEGACY_ENTRY_FILENAME, legacy_field


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_brief"


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "mini_brief"
    copytree(FIXTURE_ROOT, root)
    return root


def test_extract_current_mount_from_root_identity(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)

    mount = extract_current_mount(load_corpus(config), config)

    assert mount is not None
    assert mount.corpus_uri == "corpus://cmikeb/work/brief"
    assert mount.mount_uri == "corpus://cmikeb/work/brief@bilby"
    assert mount.owner_id == "cmikeb"
    assert mount.realm == "work"
    assert mount.tier == "BRIEF"
    assert mount.node_id == "bilby"
    assert mount.sync_transport == "git"
    assert "work/brief" in mount.aliases
    assert "work/brief@bilby" in mount.aliases


def test_extract_current_mount_from_legacy_root_identity(tmp_path):
    root = copy_fixture(tmp_path)
    canonical = root / "CORPUS.md"
    legacy = root / LEGACY_ENTRY_FILENAME
    text = canonical.read_text(encoding="utf-8")
    text = (
        text.replace("doc_type: corpus-entry", f"doc_type: {LEGACY_ENTRY_DOC_TYPE}")
        .replace("corpus_spec_version:", f"{legacy_field('version')}:")
        .replace("corpus_spec_profile:", f"{legacy_field('profile')}:")
        .replace("corpus_spec_adoption:", f"{legacy_field('adoption')}:")
        .replace("corpus_spec_reviewed:", f"{legacy_field('reviewed')}:")
        .replace("corpus_spec_betas:", f"{legacy_field('betas')}:")
        .replace("corpus_spec_corpus_uri:", f"{legacy_field('corpus_uri')}:")
        .replace("corpus_spec_mount_uri:", f"{legacy_field('mount_uri')}:")
        .replace("corpus_spec_owner_id:", f"{legacy_field('owner_id')}:")
        .replace("corpus_spec_realm:", f"{legacy_field('realm')}:")
        .replace("corpus_spec_tier:", f"{legacy_field('tier')}:")
        .replace("corpus_spec_node_id:", f"{legacy_field('node_id')}:")
        .replace("corpus_spec_sync_transport:", f"{legacy_field('sync_transport')}:")
    )
    legacy.write_text(text, encoding="utf-8")
    canonical.unlink()
    config = CatalogConfig(corpus_root=root)

    mount = extract_current_mount(load_corpus(config), config)

    assert mount is not None
    assert mount.corpus_uri == "corpus://cmikeb/work/brief"
    assert mount.mount_uri == "corpus://cmikeb/work/brief@bilby"
    assert mount.sync_transport == "git"


def test_resolve_current_mount_selector_accepts_uri_and_alias(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)
    mount = extract_current_mount(load_corpus(config), config)

    assert (
        resolve_current_mount_selector(
            mount,
            corpus_selector="corpus://cmikeb/work/brief",
        )
        == mount
    )
    assert (
        resolve_current_mount_selector(
            mount,
            corpus_selector="work/brief",
            mount_selector="work/brief@bilby",
        )
        == mount
    )


def test_resolve_current_mount_selector_rejects_other_mount(tmp_path):
    root = copy_fixture(tmp_path)
    config = CatalogConfig(corpus_root=root)
    mount = extract_current_mount(load_corpus(config), config)

    with pytest.raises(CorpusIdentityError):
        resolve_current_mount_selector(mount, corpus_selector="icloud/brief")


def test_partial_identity_does_not_mint_missing_uri(tmp_path):
    root = copy_fixture(tmp_path)
    handbook = root / "CORPUS.md"
    text = handbook.read_text(encoding="utf-8")
    handbook.write_text(
        text.replace("corpus_spec_mount_uri: corpus://cmikeb/work/brief@bilby\n", ""),
        encoding="utf-8",
    )
    config = CatalogConfig(corpus_root=root)

    with pytest.raises(CorpusIdentityError):
        extract_current_mount(load_corpus(config), config)


def test_mount_inventory_registers_current_mount(tmp_path, monkeypatch):
    root = copy_fixture(tmp_path)
    registry_home = tmp_path / "corpus-home"
    monkeypatch.setenv("CORPUS_HOME", str(registry_home))
    config = CatalogConfig(corpus_root=root)

    inventory = build_mount_inventory(load_corpus(config), config)

    registry_path = registry_home / "mounts.json"
    assert inventory.registry_path == str(registry_path)
    assert inventory.registry_updated is True
    assert registry_path.exists()
    assert [mount.mount_uri for mount in inventory.known_mounts] == [
        "corpus://cmikeb/work/brief@bilby"
    ]
    assert inventory.sync_status is not None
    assert inventory.sync_status.realm == "work"
