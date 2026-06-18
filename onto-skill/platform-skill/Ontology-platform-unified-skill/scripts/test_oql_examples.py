#!/usr/bin/env python3
"""Regression checks for OQL examples and common invalid cases."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from oql_validator import validate_oql_dict

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    ROOT / "examples" / "query.example.json",
    ROOT / "examples" / "association-query.example.json",
    ROOT / "examples" / "agg.example.json",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_valid(path: Path) -> None:
    errors = validate_oql_dict(load(path))
    if errors:
        raise AssertionError(f"{path} should be valid: {errors}")


def assert_invalid(name: str, oql: dict) -> None:
    errors = validate_oql_dict(oql)
    if not errors:
        raise AssertionError(f"{name} should be invalid")


def main() -> int:
    for example in EXAMPLES:
        assert_valid(example)

    query = load(ROOT / "examples" / "query.example.json")
    invalid_max_results = copy.deepcopy(query)
    invalid_max_results["maxResults"] = {"limit": 10, "offset": 0}
    assert_invalid("maxResults object format", invalid_max_results)

    invalid_id_name_field = copy.deepcopy(query)
    invalid_id_name_field["returns"] = [{"kind": "FIELDS", "ref": "o", "fields": ["NAME(id)"]}]
    assert_invalid("ID/NAME in FIELDS", invalid_id_name_field)

    invalid_expr_id_name = copy.deepcopy(query)
    invalid_expr_id_name["returns"] = [{"kind": "EXPR", "expr": {"kind": "FUNCTION", "name": "NAME", "args": []}, "alias": "name"}]
    assert_invalid("ID/NAME legacy EXPR function", invalid_expr_id_name)

    aggregate = load(ROOT / "examples" / "agg.example.json")
    invalid_aggregate_function = copy.deepcopy(aggregate)
    invalid_aggregate_function["returns"].append({"kind": "FUNCTION", "ref": "o", "field": "NAME(id)", "alias": "id_name"})
    assert_invalid("ID/NAME in AGGREGATE", invalid_aggregate_function)

    print("OQL example regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
