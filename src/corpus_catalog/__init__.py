"""AI-SPEC Catalog CLI and library surface."""

from corpus_catalog.config import CatalogConfig
from corpus_catalog.context import build_context_packet
from corpus_catalog.corpus import load_corpus, search_corpus
from corpus_catalog.models import (
    CatalogQuery,
    CorpusIdentity,
    ContextItem,
    ContextPacket,
    CorpusItem,
    CorpusMount,
    KnownCorpusMount,
    MountInventory,
    MountSyncStatus,
    SourceRef,
    ValidationIssue,
)

__all__ = [
    "CatalogConfig",
    "CatalogQuery",
    "ContextItem",
    "ContextPacket",
    "CorpusIdentity",
    "CorpusItem",
    "CorpusMount",
    "KnownCorpusMount",
    "MountInventory",
    "MountSyncStatus",
    "SourceRef",
    "ValidationIssue",
    "build_context_packet",
    "load_corpus",
    "search_corpus",
]
