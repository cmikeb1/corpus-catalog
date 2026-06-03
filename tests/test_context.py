from pathlib import Path

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.context import build_context_packet


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_brief"


def test_context_packet_includes_cascading_sources():
    config = CatalogConfig(corpus_root=FIXTURE_ROOT)
    packet = build_context_packet(
        goal="I am editing a project TASKS.md; what rules and state matter?",
        cwd="projects/demo/assets/epics/001-DEMO",
        config=config,
    )

    paths = [item.source.path for item in packet.items]

    assert "AI.md" in paths
    assert "projects/demo/AI.md" in paths
    assert "projects/demo/assets/OVERVIEW.md" in paths
    assert "projects/demo/assets/epics/001-DEMO/TASKS.md" in paths
    assert not packet.validation_issues


def test_context_packet_uses_bounded_excerpts():
    config = CatalogConfig(corpus_root=FIXTURE_ROOT, max_context_item_chars=200)
    packet = build_context_packet(
        goal="Tell me about demo project guidance",
        cwd="projects/demo/assets/epics/001-DEMO",
        config=config,
    )

    assert all(len(item.excerpt) <= 240 for item in packet.items)
