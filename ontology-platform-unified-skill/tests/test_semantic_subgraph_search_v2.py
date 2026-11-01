"""Offline contract regressions for the V2 subgraph Skill wrapper (unittest)."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "semantic_subgraph_search.py"


def load_skill_script():
    trace_stub = types.ModuleType("trace_utils")
    trace_stub.build_headers = lambda context, tenant: {"X-Tenant-Id": tenant}
    trace_stub.get_context_by_session = lambda session: {}
    with mock.patch.dict(sys.modules, {"trace_utils": trace_stub}):
        spec = importlib.util.spec_from_file_location("oag_v2_script_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, code, body=None):
        self.status_code = code
        self.body = body

    def json(self):
        return self.body


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.last_url = None
        self.last_kwargs = None

    def post(self, url, **kwargs):
        self.last_url, self.last_kwargs = url, kwargs
        return self.response


class V2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_skill_script()

    def test_query_only_v2_request(self):
        p = self.api.build_payload(ontology_id="ont", query="查 Account")
        self.assertEqual(p["ontologyId"], "ont")
        self.assertEqual(p["adaptiveRetrieval"], 1)
        self.assertEqual(p["topk"], 3)
        self.assertNotIn("topK", p)
        self.assertNotIn("entities", p)

    def test_entities_only_is_json_string_and_adaptive_zero(self):
        e = {"entities": {"extractedEntities": [{"objectType": "Account"}]}}
        p = self.api.build_payload(ontology_id="ont", entities=e)
        self.assertEqual(p["adaptiveRetrieval"], 0)
        self.assertIsInstance(p["entities"], str)
        self.assertEqual(json.loads(p["entities"]), e)

    def test_entities_priority_and_optional_property_filter(self):
        e = {"extractedEntities": [{"objectType": "Account"}],
             "propertyValues": [{"objectType": "Account", "propertyValues": [{"value": "1234567890"}]}]}
        p = self.api.build_payload(ontology_id="ont", query="账户", entities=e)
        self.assertEqual(json.loads(p["entities"])["entities"], e)
        self.assertEqual(p["query"], "账户")

    def test_empty_anchors_rejected_even_with_value_groups(self):
        bad = {"extractedEntities": [],
               "propertyValues": [{"objectType": "Account", "propertyValues": [{"value": "x"}]}]}
        with self.assertRaises(self.api.InputError):
            self.api.build_payload(ontology_id="ont", entities=bad)

    def test_explicit_zero_and_old_cli_topk_alias(self):
        args = self.api.get_parser().parse_args([
            "--query-json",
            json.dumps({"ontologyId": "ont", "query": "q", "includeFunctions": 0,
                        "adaptiveRetrieval": 0, "topk": 2})])
        p = self.api.payload_from_args(args)
        self.assertEqual(p["includeFunctions"], 0)
        self.assertEqual(p["adaptiveRetrieval"], 0)
        self.assertEqual(p["topk"], 2)
        args2 = self.api.get_parser().parse_args(["--ontology-id", "ont", "--query", "q", "--topK", "1"])
        self.assertEqual(self.api.payload_from_args(args2)["topk"], 1)

    def test_success_and_preserve_v2_response(self):
        p = self.api.build_payload(ontology_id="ont", query="q")
        body = {"resultCode": "200", "resultMessage": "success",
                "result": {"nodes": [{"id": "p", "label": "property",
                                      "properties": {"dataType": "enum"},
                                      "propertyEnumValues": [{"value": "Prepaid"}]}],
                           "edges": [], "functions": [], "actions": []}}
        with mock.patch.dict(os.environ, {"SERVICE_NAMESPACE": "cnai-system", "TENANT_ID": "tenantA"}):
            s = FakeSession(FakeResponse(200, body))
            result = self.api.post_subgraph(p, session=s)
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], body)
        self.assertIn("/v2/onto-retrieval/subgraph/semantic-search", s.last_url)
        self.assertNotIn("/v1/", s.last_url)
        self.assertEqual(s.last_kwargs["json"]["ontologyId"], "ont")

    def test_http_and_business_error_are_not_success(self):
        p = self.api.build_payload(ontology_id="ont", query="q")
        with mock.patch.dict(os.environ, {"SERVICE_NAMESPACE": "cnai-system", "TENANT_ID": "tenantA"}):
            http = self.api.post_subgraph(p, session=FakeSession(FakeResponse(400)))
            biz = self.api.post_subgraph(p, session=FakeSession(
                FakeResponse(200, {"resultCode": 501, "resultMessage": "bad", "result": None})))
        self.assertFalse(http["success"])
        self.assertEqual(http["error"]["code"], "HTTP_ERROR")
        self.assertFalse(biz["success"])
        self.assertEqual(biz["error"]["code"], "OAG_BUSINESS_ERROR")


if __name__ == "__main__":
    unittest.main()
