import json
import sys
from pathlib import Path
from shutil import copytree

from ai_spec_catalog.cli import main


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_brief"


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "mini_brief"
    copytree(FIXTURE_ROOT, root)
    return root


def test_index_defaults_root_to_current_working_directory(
    tmp_path, monkeypatch, capsys
):
    root = copy_fixture(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "argv", ["catalog", "index"])

    main()

    output = capsys.readouterr().out
    manifest = json.loads(output)
    assert manifest["corpus_root"] == str(root.resolve())
    assert manifest["catalog_dir"] == str(root.resolve() / ".corpus")
    assert manifest["source_count"] == 6


def test_no_args_defaults_to_status_in_corpus_root(tmp_path, monkeypatch, capsys):
    root = copy_fixture(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "argv", ["catalog"])

    main()

    output = capsys.readouterr().out
    assert "Catalog state: missing" in output
    assert f"Corpus root: {root.resolve()}" in output
    assert f"Generated state dir: {root.resolve() / '.corpus'}" in output


def test_no_args_prints_help_outside_corpus_root(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["catalog"])

    main()

    output = capsys.readouterr().out
    assert "usage: catalog" in output
    assert "Catalog state:" not in output


def test_no_args_ignores_legacy_catalog_directory(tmp_path, monkeypatch, capsys):
    (tmp_path / ".catalog").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["catalog"])

    main()

    output = capsys.readouterr().out
    assert "usage: catalog" in output
    assert "Catalog state:" not in output


def test_search_cli_emits_compact_results(tmp_path, monkeypatch, capsys):
    root = copy_fixture(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "argv", ["catalog", "index"])
    main()
    capsys.readouterr()

    monkeypatch.setattr(
        sys,
        "argv",
        ["catalog", "search", "--query", "demo project", "--limit", "1"],
    )
    main()

    results = json.loads(capsys.readouterr().out)
    assert len(results) == 1
    assert set(results[0]) == {
        "source",
        "title",
        "snippet",
        "metadata",
        "content_hash",
    }
    assert "text" not in results[0]
    assert results[0]["snippet"]
    assert len(results[0]["snippet"]) < 400
    assert "## Active Epics" not in json.dumps(results)


def test_search_cli_sees_epic_local_reference(tmp_path, monkeypatch, capsys):
    root = copy_fixture(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "argv", ["catalog", "index"])
    main()
    capsys.readouterr()

    monkeypatch.setattr(
        sys,
        "argv",
        ["catalog", "search", "--query", "demo candidate detail", "--limit", "1"],
    )
    main()

    results = json.loads(capsys.readouterr().out)
    assert len(results) == 1
    assert (
        results[0]["source"]["path"]
        == "projects/demo/assets/epics/001-DEMO/reference/demo-candidate.md"
    )
