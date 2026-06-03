from __future__ import annotations

from pathlib import Path

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.context import build_context_packet
from ai_spec_catalog.corpus import search_corpus
from ai_spec_catalog.models import ContextPacket, CorpusItem, ValidationIssue
from ai_spec_catalog.storage import index_catalog, load_index_or_corpus
from ai_spec_catalog.validators import validate_corpus


def get_context_packet(root: str | Path, goal: str, cwd: str | Path | None) -> ContextPacket:
    config = CatalogConfig(corpus_root=Path(root))
    return build_context_packet(goal=goal, cwd=cwd, config=config)


def search_catalog(root: str | Path, query: str, limit: int = 10) -> list[CorpusItem]:
    config = CatalogConfig(corpus_root=Path(root), max_search_results=limit)
    return search_corpus(query, load_index_or_corpus(config), limit=limit)


def validate_scope(root: str | Path) -> list[ValidationIssue]:
    config = CatalogConfig(corpus_root=Path(root))
    index_catalog(config)
    return validate_corpus(load_index_or_corpus(config), config)
