#!/usr/bin/env python3
"""Regression checks for OQL validation contracts."""
from __future__ import annotations

import copy

from oql_validator import validate_oql_dict


def query_sample() -> dict:
    return {
        "version": "1.0",
        "schemaRef": "example-v1",
        "strict": True,
        "operation": "QUERY",
        "objects": [{"objectType": "ExampleObject", "alias": "o"}],
        "returns": [{"kind": "FIELDS", "ref": "o", "fields": ["id"]}],
        "maxResults": 10,
    }


def berth_plan_ship_info_query_sample() -> dict:
    """End-to-end expected OQL for berth-plan-ontology ship_info query."""
    return {
        "version": "1.0",
        "schemaRef": "dtmi.ontology.560d88f7.1",
        "strict": True,
        "operation": "QUERY",
        "objects": [{"objectType": "ship_info", "alias": "s"}],
        "conditions": {
            "kind": "GROUP",
            "relation": "AND",
            "children": [
                {"kind": "PREDICATE", "ref": "s", "field": "ship_height", "operator": "GT", "values": ["10"]},
                {"kind": "PREDICATE", "ref": "s", "field": "ship_height", "operator": "LT", "values": ["30"]},
                {"kind": "PREDICATE", "ref": "s", "field": "ship_type", "operator": "EQ", "values": ["货轮"]},
                {"kind": "PREDICATE", "ref": "s", "field": "draft", "operator": "EQ", "values": ["10"]},
            ],
        },
        "returns": [
            {"kind": "FIELDS", "ref": "s", "fields": ["ship_no", "ship_type", "ship_height", "draft", "loa"]}
        ],
        "maxResults": 1000,
    }


def association_sample() -> dict:
    return {
        "version": "1.0",
        "schemaRef": "example-v1",
        "strict": True,
        "operation": "ASSOCIATION_QUERY",
        "objects": [
            {"objectType": "SourceObject", "alias": "s"},
            {"objectType": "TargetObject", "alias": "t"},
        ],
        "relationships": [{"relationshipType": "connects", "alias": "r1", "from": "s", "to": "t"}],
        "returns": [
            {"kind": "FIELDS", "ref": "s", "fields": ["id"]},
            {"kind": "FIELDS", "ref": "r1", "fields": ["id"]},
            {"kind": "FIELDS", "ref": "t", "fields": ["id"]},
        ],
        "maxResults": 10,
    }


def aggregate_sample() -> dict:
    return {
        "version": "1.0",
        "schemaRef": "example-v1",
        "strict": True,
        "operation": "AGGREGATE",
        "objects": [{"objectType": "ExampleObject", "alias": "o"}],
        "returns": [{"kind": "METRIC", "function": "COUNT", "ref": "o", "field": "id", "alias": "cnt"}],
        "maxResults": 10,
    }


def assert_valid(name: str, oql: dict) -> None:
    errors = validate_oql_dict(oql)
    if errors:
        raise AssertionError(f"{name} should be valid: {errors}")


def assert_invalid(name: str, oql: dict) -> None:
    errors = validate_oql_dict(oql)
    if not errors:
        raise AssertionError(f"{name} should be invalid")


def main() -> int:
    query = query_sample()
    berth_query = berth_plan_ship_info_query_sample()
    association = association_sample()
    aggregate = aggregate_sample()

    assert_valid("QUERY sample", query)
    assert_valid("berth-plan ship_info QUERY sample", berth_query)
    assert_valid("ASSOCIATION_QUERY sample", association)
    assert_valid("AGGREGATE sample", aggregate)

    invalid_max_results = copy.deepcopy(query)
    invalid_max_results["maxResults"] = {"limit": 10, "offset": 0}
    assert_invalid("maxResults object format", invalid_max_results)

    invalid_query_version = copy.deepcopy(berth_query)
    invalid_query_version["version"] = "2.0"
    assert_invalid("non-initial OQL version 2.0", invalid_query_version)

    invalid_id_name_field = copy.deepcopy(query)
    invalid_id_name_field["returns"] = [{"kind": "FIELDS", "ref": "o", "fields": ["NAME(id)"]}]
    assert_invalid("ID/NAME in FIELDS", invalid_id_name_field)

    invalid_expr_id_name = copy.deepcopy(query)
    invalid_expr_id_name["returns"] = [{"kind": "EXPR", "expr": {"kind": "FUNCTION", "name": "NAME", "args": []}, "alias": "name"}]
    assert_invalid("ID/NAME legacy EXPR function", invalid_expr_id_name)

    invalid_aggregate_function = copy.deepcopy(aggregate)
    invalid_aggregate_function["returns"].append({"kind": "FUNCTION", "ref": "o", "field": "NAME(id)", "alias": "id_name"})
    assert_invalid("ID/NAME in AGGREGATE", invalid_aggregate_function)

    print("OQL validation contract checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())