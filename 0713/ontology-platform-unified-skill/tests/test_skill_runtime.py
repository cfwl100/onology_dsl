from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from skill_runtime import build_oag_payload, detect_intent, detect_operation, normalize_oql, plan_service_request  # noqa: E402


class SkillRuntimeTest(unittest.TestCase):
    def test_detect_operation_aggregate(self) -> None:
        self.assertEqual(detect_operation("统计最近三天告警数量"), "AGGREGATE")

    def test_detect_operation_association(self) -> None:
        self.assertEqual(detect_operation("查询站点附近小区"), "ASSOCIATION_QUERY")

    def test_detect_operation_query_default(self) -> None:
        self.assertEqual(detect_operation("查询站点详情"), "QUERY")

    def test_detect_intent_ticket(self) -> None:
        self.assertEqual(detect_intent("请自动创建工单"), "TICKET_CREATE")

    def test_build_oag_payload(self) -> None:
        payload = build_oag_payload("查询站点附近小区", ontology_id="demo@1.0")
        self.assertEqual(payload["ontology-id"], "demo@1.0")
        self.assertIn("query", payload)

    def test_plan_service_request_contains_route(self) -> None:
        plan = plan_service_request("统计工单数量", ontology_id="demo@1.0")
        self.assertEqual(plan["operation"], "AGGREGATE")
        self.assertTrue(plan["route"]["needs_oag"])
        self.assertTrue(plan["route"]["needs_oac"])

    def test_normalize_oql(self) -> None:
        oql = normalize_oql({"operation": "query", "objects": [], "returns": []}, ontology_id="demo@1.0")
        self.assertEqual(oql["operation"], "QUERY")
        self.assertEqual(oql["schemaRef"], "demo@1.0")
        self.assertEqual(oql["version"], "1.0")
        self.assertTrue(oql["strict"])
        self.assertEqual(oql["maxResults"], 1000)


if __name__ == "__main__":
    unittest.main()
