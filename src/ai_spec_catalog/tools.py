from __future__ import annotations

from pathlib import Path

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.context import build_context_packet
from ai_spec_catalog.corpus import search_corpus
from ai_spec_catalog.identity import extract_current_mount, resolve_current_mount_selector
from ai_spec_catalog.models import ContextPacket, CorpusItem, ValidationIssue
from ai_spec_catalog.storage import index_catalog, load_index_or_corpus
from ai_spec_catalog.validators import validate_corpus


def get_context_packet(
    root: str | Path,
    goal: str,
    cwd: str | Path | None,
    corpus: str | None = None,
    mount: str | None = None,
) -> ContextPacket:
    config = CatalogConfig(corpus_root=Path(root))
    ensure_identity_selection(config, corpus, mount)
    return build_context_packet(goal=goal, cwd=cwd, config=config)


def search_catalog(
    root: str | Path,
    query: str,
    limit: int = 10,
    corpus: str | None = None,
    mount: str | None = None,
) -> list[CorpusItem]:
    config = CatalogConfig(corpus_root=Path(root), max_search_results=limit)
    ensure_identity_selection(config, corpus, mount)
    return search_corpus(query, load_index_or_corpus(config), limit=limit)


def validate_scope(
    root: str | Path,
    corpus: str | None = None,
    mount: str | None = None,
) -> list[ValidationIssue]:
    config = CatalogConfig(corpus_root=Path(root))
    ensure_identity_selection(config, corpus, mount)
    index_catalog(config)
    return validate_corpus(load_index_or_corpus(config), config)


def ensure_identity_selection(
    config: CatalogConfig,
    corpus: str | None,
    mount: str | None,
) -> None:
    current_mount = extract_current_mount(load_index_or_corpus(config), config)
    resolve_current_mount_selector(
        current_mount,
        corpus_selector=corpus,
        mount_selector=mount,
    )
