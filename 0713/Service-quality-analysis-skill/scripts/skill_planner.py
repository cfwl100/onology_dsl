#!/usr/bin/env python3
"""Deterministic planner for the service-quality-analysis skill.

The planner converts a user question into a compact execution plan so the
orchestration layer no longer needs to spend multiple LLM calls on route
selection, OAG payload preparation, and cache-key generation.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
UNIFIED_SCRIPTS = CURRENT_DIR.parents[2] / "ontology-platform-unified-skill" / "scripts"
if str(UNIFIED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(UNIFIED_SCRIPTS))

from skill_runtime import compact_json, load_cache, plan_service_request, store_cache  # noqa: E402


def _load_entity_hints(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("--entity-hints-json must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic planner for service-quality-analysis")
    parser.add_argument("--question", required=True, help="User question or task description")
    parser.add_argument("--ontology-id", default=os.environ.get("ONTOLOGY_ID"), help="Ontology ID")
    parser.add_argument("--entity-hints-json", help="Optional JSON object with known entity hints")
    parser.add_argument("--cache-dir", default=str(CURRENT_DIR / ".skill-cache"), help="Cache directory")
    parser.add_argument("--no-cache", action="store_true", help="Disable plan cache")
    parser.add_argument("--output", help="Write the compact plan JSON to a file")
    parser.add_argument("--top-k", type=int, default=3, help="TopK for OAG payload")
    parser.add_argument("--include-functions", type=int, default=0, help="Force includeFunctions in OAG payload")
    args = parser.parse_args()

    entity_hints = _load_entity_hints(args.entity_hints_json)
    plan = plan_service_request(
        args.question,
        args.ontology_id,
        entity_hints=entity_hints,
        top_k=args.top_k,
        include_functions=args.include_functions,
    )

    if not args.no_cache:
        cached = load_cache(args.cache_dir, plan["cache_key"])
        if isinstance(cached, dict):
            plan = cached
        else:
            store_cache(args.cache_dir, plan["cache_key"], plan)

    output = compact_json(plan)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
