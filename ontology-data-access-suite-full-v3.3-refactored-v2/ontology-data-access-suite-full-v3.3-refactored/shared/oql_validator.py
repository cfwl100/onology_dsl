
#!/usr/bin/env python3
"""Structural validator for canonical OQL (expression-aware)."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Dict, List, Set
READ_OPS = {"QUERY", "AGGREGATE", "ASSOCIATION_QUERY", "LINK_QUERY"}
WRITE_OPS = {"CREATE", "UPDATE", "DELETE", "UPSERT", "BATCH"}
ALL_OPS = READ_OPS | WRITE_OPS
ALLOWED_TOP = {"version","schemaRef","strict","operation","objects","relationships","conditions","returns","orders","maxResults","sourceQuery","linkQuery","mutation","options","extensions"}
CONDITION_OPERATORS = {"EQ":1,"NE":1,"GT":1,"GTE":1,"LT":1,"LTE":1,"IN":"many","NOT_IN":"many","BETWEEN":2,"LIKE":1,"CONTAINS":1,"STARTS_WITH":1,"ENDS_WITH":1,"IS_NULL":0,"IS_NOT_NULL":0}
RETURN_KINDS = {"FIELDS","EXPR","GROUP_BY","METRIC"}
METRIC_FUNCTIONS = {"COUNT","SUM","AVG","MIN","MAX"}
class ValidationError(Exception):
    pass
def assert_true(cond: bool, msg: str):
    if not cond: raise ValidationError(msg)
def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
def validate_expr(value: Any, allowed_refs: Set[str] | None = None):
    assert_true(isinstance(value, dict), "expression must be object")
    kind = value.get("kind")
    assert_true(kind in {"FUNCTION","FIELD_REF"}, f"unsupported expression kind: {kind}")
    if kind == "FIELD_REF":
        ref, field = value.get("ref"), value.get("field")
        assert_true(isinstance(ref, str) and ref, "FIELD_REF.ref is required")
        assert_true(isinstance(field, str) and field, "FIELD_REF.field is required")
        if allowed_refs is not None: assert_true(ref in allowed_refs, f"FIELD_REF.ref must reference known alias: {ref}")
        return
    name, args = value.get("name"), value.get("args")
    assert_true(isinstance(name, str) and name, "FUNCTION.name is required")
    assert_true(isinstance(args, list), "FUNCTION.args must be array")
    for arg in args:
        if isinstance(arg, dict) and arg.get("kind") in {"FUNCTION","FIELD_REF"}:
            validate_expr(arg, allowed_refs)
def validate_aliases(objects: List[Dict[str, Any]]) -> Set[str]:
    aliases: Set[str] = set()
    for obj in objects:
        assert_true(isinstance(obj, dict), "objects items must be objects")
        assert_true(isinstance(obj.get("objectType"), str) and obj["objectType"], "objectType is required")
        assert_true(isinstance(obj.get("alias"), str) and obj["alias"], "object alias is required")
        assert_true(obj["alias"] not in aliases, f"duplicate object alias: {obj['alias']}")
        aliases.add(obj["alias"])
        if "fromSource" in obj: assert_true(isinstance(obj["fromSource"], str) and obj["fromSource"], "fromSource must be non-empty string")
    return aliases
def validate_relationships(relationships: List[Dict[str, Any]], object_aliases: Set[str]) -> Set[str]:
    rel_aliases: Set[str] = set()
    for rel in relationships:
        assert_true(isinstance(rel, dict), "relationships items must be objects")
        for field in ("relationshipType","alias","from","to"):
            assert_true(isinstance(rel.get(field), str) and rel[field], f"relationship {field} is required")
        assert_true(rel["alias"] not in rel_aliases, f"duplicate relationship alias: {rel['alias']}")
        assert_true(rel["alias"] not in object_aliases, f"relationship alias conflicts with object alias: {rel['alias']}")
        assert_true(rel["from"] in object_aliases, f"relationship.from unknown alias: {rel['from']}")
        assert_true(rel["to"] in object_aliases, f"relationship.to unknown alias: {rel['to']}")
        rel_aliases.add(rel["alias"])
    return rel_aliases
def validate_conditions(node: Dict[str, Any], allowed_refs: Set[str]):
    assert_true(isinstance(node, dict), "conditions must be object")
    kind = node.get("kind")
    assert_true(kind in {"GROUP","PREDICATE"}, "conditions.kind must be GROUP or PREDICATE")
    if kind == "GROUP":
        relation, children = node.get("relation"), node.get("children")
        assert_true(relation in {"AND","OR","NOT"}, "GROUP relation must be AND/OR/NOT")
        assert_true(isinstance(children, list) and children, "GROUP children must be non-empty array")
        if relation == "NOT": assert_true(len(children) == 1, "NOT group must contain exactly one child")
        for child in children: validate_conditions(child, allowed_refs)
        return
    op = node.get("operator")
    assert_true(op in CONDITION_OPERATORS, f"unsupported operator: {op}")
    has_simple = isinstance(node.get("ref"), str) and isinstance(node.get("field"), str)
    has_expr = isinstance(node.get("leftExpr"), dict)
    assert_true(has_simple or has_expr, "PREDICATE requires ref/field or leftExpr")
    if has_simple: assert_true(node["ref"] in allowed_refs, f"PREDICATE ref must be known alias: {node['ref']}")
    if has_expr: validate_expr(node["leftExpr"], allowed_refs)
    expected = CONDITION_OPERATORS[op]
    if expected == 0:
        assert_true("values" not in node, f"operator {op} must not contain values")
    else:
        values = node.get("values")
        assert_true(isinstance(values, list), f"operator {op} requires values array")
        if expected == 1: assert_true(len(values) == 1, f"operator {op} requires exactly one value")
        elif expected == 2: assert_true(len(values) == 2, f"operator {op} requires exactly two values")
        else: assert_true(len(values) >= 1, f"operator {op} requires at least one value")
        for value in values:
            if isinstance(value, dict) and value.get("kind") in {"FUNCTION","FIELD_REF"}: validate_expr(value, allowed_refs)
def validate_returns(items: List[Dict[str, Any]], allowed_refs: Set[str], operation: str):
    assert_true(isinstance(items, list) and items, "returns must be non-empty array")
    metric_count = 0
    for item in items:
        assert_true(isinstance(item, dict), "returns items must be objects")
        kind = item.get("kind")
        assert_true(kind in RETURN_KINDS, f"unsupported returns.kind: {kind}")
        if kind == "FIELDS":
            assert_true(isinstance(item.get("ref"), str) and item["ref"] in allowed_refs, f"FIELDS.ref must be known alias: {item.get('ref')}")
            assert_true(isinstance(item.get("fields"), list) and item["fields"], "FIELDS requires non-empty fields array")
        elif kind == "EXPR":
            validate_expr(item.get("expr"), allowed_refs)
            assert_true(isinstance(item.get("alias"), str) and item["alias"], "EXPR requires alias")
        elif kind == "GROUP_BY":
            assert_true(isinstance(item.get("alias"), str) and item["alias"], "GROUP_BY requires alias")
            if "expr" in item: validate_expr(item["expr"], allowed_refs)
            else:
                assert_true(isinstance(item.get("ref"), str) and item["ref"] in allowed_refs, f"GROUP_BY.ref must be known alias: {item.get('ref')}")
                assert_true(isinstance(item.get("field"), str) and item["field"], "GROUP_BY.field is required")
        elif kind == "METRIC":
            metric_count += 1
            assert_true(isinstance(item.get("ref"), str) and item["ref"] in allowed_refs, f"METRIC.ref must be known alias: {item.get('ref')}")
            assert_true(isinstance(item.get("field"), str) and item["field"], "METRIC.field is required")
            assert_true(item.get("function") in METRIC_FUNCTIONS, f"METRIC.function invalid: {item.get('function')}")
            assert_true(isinstance(item.get("alias"), str) and item["alias"], "METRIC.alias is required")
            if item["function"] != "COUNT": assert_true(item["field"] != "*", "only COUNT may use field='*'")
    if operation == "AGGREGATE":
        assert_true(metric_count >= 1, "AGGREGATE requires at least one METRIC")
        assert_true(all(i.get("kind") in {"GROUP_BY","METRIC"} for i in items), "AGGREGATE returns may contain only GROUP_BY and METRIC")
    if operation == "QUERY":
        assert_true(all(i.get("kind") in {"FIELDS","EXPR"} for i in items), "QUERY returns may contain only FIELDS and EXPR")
def validate_orders(items: List[Dict[str, Any]]):
    assert_true(isinstance(items, list) and items, "orders must be non-empty array")
    for item in items:
        assert_true(isinstance(item, dict), "orders items must be objects")
        assert_true(isinstance(item.get("ref"), str) and item["ref"], "orders.ref is required")
        assert_true(isinstance(item.get("field"), str) and item["field"], "orders.field is required")
        assert_true(item.get("direction") in {"ASC","DESC"}, "orders.direction must be ASC or DESC")
def validate_source_query(items: List[Dict[str, Any]], depth: int):
    assert_true(depth <= 2, "sourceQuery nesting depth exceeds strict limit of 2")
    assert_true(isinstance(items, list) and items, "sourceQuery must be non-empty array")
    seen: Set[str] = set()
    for item in items:
        assert_true(isinstance(item, dict), "sourceQuery items must be objects")
        output_as = item.get("outputAs")
        assert_true(isinstance(output_as, str) and output_as, "sourceQuery.outputAs is required")
        assert_true(output_as not in seen, f"duplicate sourceQuery outputAs: {output_as}")
        seen.add(output_as)
        validate_oql(item, False, depth)
        assert_true(item.get("operation") in READ_OPS, "sourceQuery only supports read operations")
def validate_link_query(block: Dict[str, Any], object_aliases: Set[str]):
    assert_true(isinstance(block, dict), "linkQuery must be object")
    assert_true(block.get("mode") in {"LIST","ONE"}, "linkQuery.mode must be LIST or ONE")
    assert_true(isinstance(block.get("relationshipType"), str) and block["relationshipType"], "linkQuery.relationshipType required")
    for key in ("sourceRef","targetRef"):
        assert_true(isinstance(block.get(key), str) and block[key] in object_aliases, f"linkQuery.{key} must reference known object alias")
    if "direction" in block: assert_true(block["direction"] in {"OUTBOUND","INBOUND","BIDIRECTIONAL"}, "linkQuery.direction invalid")
def validate_mutation(block: Dict[str, Any], operation: str):
    assert_true(isinstance(block, dict), "mutation must be object")
    if operation == "CREATE":
        props = (((block.get("data") or {}).get("properties")) if isinstance(block.get("data"), dict) else None)
        assert_true(isinstance(props, dict) and props, "CREATE requires mutation.data.properties")
    elif operation == "UPDATE":
        assert_true(block.get("scope") in {"ONE","MANY"}, "UPDATE mutation.scope must be ONE or MANY")
        assert_true(isinstance(block.get("set"), dict) and block["set"], "UPDATE requires non-empty mutation.set")
    elif operation == "DELETE":
        assert_true(block.get("scope") in {"ONE","MANY"}, "DELETE mutation.scope must be ONE or MANY")
        assert_true("set" not in block and "data" not in block, "DELETE must not contain mutation.set or mutation.data")
    elif operation == "UPSERT":
        match_by = block.get("matchBy")
        props = (((block.get("data") or {}).get("properties")) if isinstance(block.get("data"), dict) else None)
        assert_true(isinstance(match_by, list) and match_by, "UPSERT requires non-empty mutation.matchBy")
        assert_true(isinstance(props, dict) and props, "UPSERT requires mutation.data.properties")
        for field in match_by: assert_true(field in props, f"UPSERT matchBy field missing from data.properties: {field}")
    elif operation == "BATCH":
        assert_true(isinstance(block.get("atomic"), bool), "BATCH requires boolean mutation.atomic")
        items = block.get("items")
        assert_true(isinstance(items, list) and items, "BATCH requires non-empty mutation.items")
        for item in items:
            assert_true(isinstance(item, dict), "BATCH items must be objects")
            assert_true(item.get("operation") in {"CREATE","UPDATE","DELETE","UPSERT"}, "BATCH items only allow CREATE/UPDATE/DELETE/UPSERT")
            assert_true(item.get("operation") != "BATCH", "nested BATCH not allowed")
            validate_oql(item, True, 0)
def validate_oql(data: Dict[str, Any], is_batch_item: bool = False, depth: int = 0):
    assert_true(isinstance(data, dict), "OQL document must be object")
    unknown = set(data.keys()) - ALLOWED_TOP - {"outputAs"}
    assert_true(not unknown, f"unknown top-level fields: {sorted(unknown)}")
    op = data.get("operation")
    assert_true(op in ALL_OPS, f"operation invalid: {op}")
    if not is_batch_item:
        assert_true(data.get("version") == "1.0", "version must be '1.0'")
        assert_true(isinstance(data.get("schemaRef"), str) and data["schemaRef"], "schemaRef is required")
        if "strict" in data: assert_true(isinstance(data["strict"], bool), "strict must be boolean")
    else:
        for inherited in ("version","schemaRef","strict"): assert_true(inherited not in data, f"BATCH items must not include {inherited}")
    if "maxResults" in data:
        assert_true(isinstance(data["maxResults"], int), "maxResults must be integer")
        assert_true(1 <= data["maxResults"] <= 100000, "maxResults must be between 1 and 100000")
    object_aliases: Set[str] = set(); relationship_aliases: Set[str] = set()
    if op != "BATCH" and "objects" in data:
        assert_true(isinstance(data["objects"], list) and data["objects"], "objects must be non-empty array")
        object_aliases = validate_aliases(data["objects"])
    if op == "ASSOCIATION_QUERY":
        assert_true("relationships" in data, "ASSOCIATION_QUERY requires relationships")
        assert_true(isinstance(data["relationships"], list) and data["relationships"], "relationships must be non-empty array")
        relationship_aliases = validate_relationships(data["relationships"], object_aliases)
    elif "relationships" in data:
        raise ValidationError("relationships only allowed in ASSOCIATION_QUERY")
    if op in READ_OPS: assert_true("returns" in data, f"{op} requires returns")
    if op in {"UPDATE","DELETE"}: assert_true("conditions" in data, f"{op} requires conditions")
    if op in {"CREATE","UPSERT"}: assert_true("conditions" not in data, f"{op} must not include conditions")
    allowed_refs = object_aliases | relationship_aliases
    if "conditions" in data: validate_conditions(data["conditions"], allowed_refs)
    if "returns" in data: validate_returns(data["returns"], allowed_refs, op)
    if "orders" in data: validate_orders(data["orders"])
    if "sourceQuery" in data:
        assert_true(op in READ_OPS, "sourceQuery only allowed in read operations")
        validate_source_query(data["sourceQuery"], depth + 1)
        outputs = {item["outputAs"] for item in data["sourceQuery"]}
        for obj in data.get("objects", []):
            if "fromSource" in obj: assert_true(obj["fromSource"] in outputs, f"objects.fromSource must reference same-level sourceQuery.outputAs: {obj['fromSource']}")
    if op == "LINK_QUERY":
        assert_true(len(data.get("objects", [])) == 2, "LINK_QUERY requires exactly two objects")
        assert_true("linkQuery" in data, "LINK_QUERY requires linkQuery block")
        validate_link_query(data["linkQuery"], object_aliases)
    elif "linkQuery" in data:
        raise ValidationError("linkQuery only allowed in LINK_QUERY")
    if op in WRITE_OPS:
        assert_true("mutation" in data, f"{op} requires mutation")
        validate_mutation(data["mutation"], op)
    elif "mutation" in data:
        raise ValidationError("mutation only allowed in write operations")
    if op in {"CREATE","UPDATE","DELETE","UPSERT"}: assert_true(len(data.get("objects", [])) == 1, f"{op} requires exactly one object")
    if op == "BATCH": assert_true("objects" not in data, "BATCH top level must not contain objects")
def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical OQL")
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    data = load_json(Path(args.input))
    try:
        validate_oql(data)
    except ValidationError as exc:
        print(json.dumps({"success": False, "errors": [{"code": "OQL_VALIDATION_ERROR", "message": str(exc)}]}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"success": True}, ensure_ascii=False, indent=2))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
