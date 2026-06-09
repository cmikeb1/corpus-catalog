from pathlib import Path

from corpus_catalog.config import CatalogConfig
from corpus_catalog.context import build_context_packet


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_brief"


def context_paths(goal: str, cwd: str) -> list[str]:
    config = CatalogConfig(corpus_root=FIXTURE_ROOT, max_context_items=20)
    packet = build_context_packet(goal=goal, cwd=cwd, config=config)
    return [item.source.path for item in packet.items]


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
    assert "projects/demo/assets/epics/001-DEMO/SPIKE.md" in paths
    assert not packet.validation_issues


def test_context_packet_uses_bounded_excerpts():
    config = CatalogConfig(corpus_root=FIXTURE_ROOT, max_context_item_chars=200)
    packet = build_context_packet(
        goal="Tell me about demo project guidance",
        cwd="projects/demo/assets/epics/001-DEMO",
        config=config,
    )

    assert all(len(item.excerpt) <= 240 for item in packet.items)


def test_context_routes_workspace_profile_by_cwd():
    paths = context_paths(
        goal="Update the workspace kanban",
        cwd="workspace",
    )

    assert paths[1] == "corpus-spec/profiles/human-workspace.md"


def test_context_routes_reference_profile_by_cwd():
    paths = context_paths(
        goal="Update shared tool reference",
        cwd="reference/tools",
    )

    assert paths[1] == "corpus-spec/profiles/reference.md"


def test_context_routes_reference_and_initiatives_profiles_by_cwd():
    paths = context_paths(
        goal="Update an initiative brief",
        cwd="reference/initiatives/demo",
    )

    assert paths[1:3] == [
        "corpus-spec/profiles/reference.md",
        "corpus-spec/profiles/initiatives.md",
    ]


def test_context_routes_catalog_tasks_to_project_and_tooling_docs():
    paths = context_paths(
        goal="Implement Catalog indexing validation generated-state behavior",
        cwd="projects/spec/code/corpus-catalog",
    )

    assert "corpus-spec/profiles/project.md" in paths
    assert "corpus-spec/specs/tooling-and-validation.md" in paths


def test_context_routes_corpus_identity_goals_to_identity_spec():
    paths = context_paths(
        goal="Implement corpus identity, realm, and mount URI behavior",
        cwd="projects/spec/code/corpus-catalog",
    )

    assert "corpus-spec/specs/corpus-identity.md" in paths


def test_context_routes_profile_module_goals_to_profile_composition_spec():
    paths = context_paths(
        goal="Review active profile modules, betas, and packaging",
        cwd="projects/demo",
    )

    assert "corpus-spec/specs/profile-composition.md" in paths
