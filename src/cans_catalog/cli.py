from __future__ import annotations

import argparse
import json
from pathlib import Path

from cans_catalog.config import CatalogConfig
from cans_catalog.context import build_context_packet
from cans_catalog.corpus import load_corpus, search_corpus
from cans_catalog.validators import validate_corpus


def main() -> None:
    parser = argparse.ArgumentParser(prog="cans-catalog")
    subparsers = parser.add_subparsers(dest="command", required=True)

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

    args = parser.parse_args()
    config = CatalogConfig(corpus_root=Path(args.root))

    if args.command == "context":
        packet = build_context_packet(goal=args.goal, cwd=args.cwd, config=config)
        print(packet.model_dump_json(indent=2))
    elif args.command == "search":
        items = search_corpus(args.query, load_corpus(config), limit=args.limit)
        print(json.dumps([item.model_dump(mode="json") for item in items], indent=2))
    elif args.command == "validate":
        issues = validate_corpus(load_corpus(config), config)
        print(json.dumps([issue.model_dump(mode="json") for issue in issues], indent=2))


if __name__ == "__main__":
    main()
