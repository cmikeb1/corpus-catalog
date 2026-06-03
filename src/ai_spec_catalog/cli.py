from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.context import build_context_packet
from ai_spec_catalog.corpus import search_corpus
from ai_spec_catalog.models import CatalogStatus
from ai_spec_catalog.projects import build_project_creation_plan
from ai_spec_catalog.storage import (
    catalog_status,
    gitignore_warning,
    index_catalog,
    init_catalog,
    load_index_or_corpus,
)
from ai_spec_catalog.validators import validate_corpus


def main() -> None:
    parser = argparse.ArgumentParser(prog="catalog")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--root", required=True)

    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("--root", required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--root", required=True)
    status_parser.add_argument("--format", choices=("text", "json"), default="text")

    context_parser = subparsers.add_parser("context")
    context_parser.add_argument("--root", required=True)
    context_parser.add_argument("--cwd")
    context_parser.add_argument("--goal", required=True)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--root", required=True)
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--limit", type=int, default=10)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--root", required=True)
    validate_parser.add_argument("--format", choices=("json", "markdown"), default="json")

    project_parser = subparsers.add_parser("project")
    project_subparsers = project_parser.add_subparsers(
        dest="project_command", required=True
    )
    project_new_parser = project_subparsers.add_parser("new")
    project_new_parser.add_argument("--root", required=True)
    project_new_parser.add_argument("--name", required=True)
    project_new_parser.add_argument("--slug")
    project_new_parser.add_argument("--tag")
    project_new_parser.add_argument("--tier")
    project_new_parser.add_argument("--lifecycle", default="DRAFT")

    args = parser.parse_args()
    config = CatalogConfig(corpus_root=Path(args.root))

    if args.command == "init":
        manifest = init_catalog(config)
        warning = gitignore_warning(config)
        if warning:
            print(f"warning: {warning}", file=sys.stderr)
        print(manifest.model_dump_json(indent=2))
    elif args.command == "index":
        manifest = index_catalog(config)
        print(manifest.model_dump_json(indent=2))
    elif args.command == "status":
        status = catalog_status(config)
        if args.format == "json":
            print(status.model_dump_json(indent=2))
        else:
            print(format_status(status))
    elif args.command == "context":
        packet = build_context_packet(goal=args.goal, cwd=args.cwd, config=config)
        print(packet.model_dump_json(indent=2))
    elif args.command == "search":
        items = search_corpus(args.query, load_index_or_corpus(config), limit=args.limit)
        print(json.dumps([item.model_dump(mode="json") for item in items], indent=2))
    elif args.command == "validate":
        index_catalog(config)
        issues = validate_corpus(load_index_or_corpus(config), config)
        if args.format == "markdown":
            report_path = config.catalog_dir / "reports" / "validation.md"
            print(report_path.read_text(encoding="utf-8"))
        else:
            print(json.dumps([issue.model_dump(mode="json") for issue in issues], indent=2))
    elif args.command == "project" and args.project_command == "new":
        plan = build_project_creation_plan(
            name=args.name,
            config=config,
            slug=args.slug,
            tag=args.tag,
            tier=args.tier,
            lifecycle=args.lifecycle,
        )
        print(plan.model_dump_json(indent=2))


def format_status(status: CatalogStatus) -> str:
    lines = [
        f"Catalog state: {status.state}",
        f"Corpus root: {status.corpus_root}",
        f"Catalog dir: {status.catalog_dir}",
    ]
    if status.manifest and status.manifest.generated_at:
        lines.append(f"Generated: {status.manifest.generated_at}")
    if status.manifest and status.manifest.ai_spec_baseline:
        lines.append(f"AI-SPEC baseline: {status.manifest.ai_spec_baseline}")
    if status.missing_artifacts:
        lines.append("Missing artifacts:")
        lines.extend(f"- {artifact}" for artifact in status.missing_artifacts)
    if status.stale_reasons:
        lines.append("Reasons:")
        lines.extend(f"- {reason}" for reason in status.stale_reasons)
    if status.next_commands:
        lines.append("Next commands:")
        lines.extend(f"- {command}" for command in status.next_commands)
    return "\n".join(lines)


if __name__ == "__main__":
    main()
