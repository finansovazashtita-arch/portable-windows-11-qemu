"""
Unit and Integration Tests for Milestone M70: Comprehensive OpenAPI Documentation,
Schema Validation Middleware, Swagger UI Rendering, and API Versioning Strategy.
"""

import http.client
import json
import os
import threading
import time
import unittest
import yaml

from src.api.openapi_docs import (
    APIVersionRouter,
    OpenAPISchemaValidator,
    get_openapi_dict,
    get_openapi_json,
    get_openapi_yaml,
    get_swagger_ui_html,
)
from src.dashboard.dashboard_server import DashboardHandler, ThreadedHTTPServer


class TestOpenAPISpecGenerator(unittest.TestCase):
    """Unit tests for OpenAPI 3.1 Spec Generator and Exporters."""

    def test_openapi_dict_structure(self):
        spec = get_openapi_dict()
        self.assertEqual(spec.get("openapi"), "3.1.0")
        self.assertEqual(spec.get("info", {}).get("version"), "2.0.0")
        self.assertIn("paths", spec)
        self.assertIn("components", spec)
        self.assertIn("/api/docs", spec["paths"])
        self.assertIn("/api/v1/telemetry", spec["paths"])
        self.assertIn("/api/v2/telemetry", spec["paths"])

    def test_openapi_json_export(self):
        json_str = get_openapi_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["openapi"], "3.1.0")
        self.assertIn("FinansProtect", parsed["info"]["title"])

    def test_openapi_yaml_export(self):
        yaml_str = get_openapi_yaml()
        parsed = yaml.safe_load(yaml_str)
        self.assertEqual(parsed["openapi"], "3.1.0")
        self.assertIn("FinansProtect", parsed["info"]["title"])

    def test_docs_yaml_file_integrity(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        yaml_path = os.path.join(root_dir, "docs", "openapi.yaml")
        self.assertTrue(os.path.exists(yaml_path), "docs/openapi.yaml must exist")

        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()

        parsed = yaml.safe_load(content)
        self.assertEqual(parsed["openapi"], "3.1.0")
        self.assertIn("/api/v1/compliance/correct", parsed["paths"])


class TestOpenAPISchemaValidator(unittest.TestCase):
    """Unit tests for OpenAPI Schema Validation Middleware."""

    def test_valid_request_payloads(self):
        valid_correction = {
            "discrepancy_id": "DISC_BG_001",
            "resolution": "RESOLVED_MANUAL_AUDIT",
            "auditor": "Senior CPA Auditor",
        }
        is_valid, errors = OpenAPISchemaValidator.validate_request("POST", "/api/v1/compliance/correct", valid_correction)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        valid_scan = {
            "ocr_text": "ФИСКАЛЕН БОН\nОБЩО: 50.00",
            "nra_qr_string": "12345*2026-01-01*50.00",
        }
        is_valid, errors = OpenAPISchemaValidator.validate_request("POST", "/api/v1/mobile/scan", valid_scan)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_missing_required_properties(self):
        invalid_correction = {
            "resolution": "RESOLVED_MANUAL_AUDIT"
        }
        is_valid, errors = OpenAPISchemaValidator.validate_request("POST", "/api/v1/compliance/correct", invalid_correction)
        self.assertFalse(is_valid)
        self.assertTrue(any("discrepancy_id" in err for err in errors))

    def test_invalid_property_data_types(self):
        invalid_type_scan = {
            "ocr_text": 1234567,  # Expected string
        }
        is_valid, errors = OpenAPISchemaValidator.validate_request("POST", "/api/v1/mobile/scan", invalid_type_scan)
        self.assertFalse(is_valid)
        self.assertTrue(any("must be string" in err for err in errors))


class TestAPIVersionRouter(unittest.TestCase):
    """Unit tests for API Version Routing logic."""

    def test_path_version_resolution(self):
        canon, ver = APIVersionRouter.resolve_version_and_route("/api/v1/telemetry")
        self.assertEqual(canon, "/api/v1/telemetry")
        self.assertEqual(ver, "v1")

        canon, ver = APIVersionRouter.resolve_version_and_route("/api/v2/telemetry")
        self.assertEqual(canon, "/api/v2/telemetry")
        self.assertEqual(ver, "v2")

        canon, ver = APIVersionRouter.resolve_version_and_route("/api/telemetry")
        self.assertEqual(canon, "/api/v1/telemetry")
        self.assertEqual(ver, "v1")

    def test_header_version_override(self):
        canon, ver = APIVersionRouter.resolve_version_and_route("/api/telemetry", header_version="2.0")
        self.assertEqual(ver, "v2")


class TestOpenAPIHTTPIntegration(unittest.TestCase):
    """Integration tests for OpenAPI HTTP endpoints & Middleware in DashboardHandler."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), DashboardHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _make_request(self, method: str, path: str, body: dict = None, headers: dict = None) -> tuple[int, dict, dict, str]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers=req_headers)
        res = conn.getresponse()
        status = res.status
        resp_headers = dict(res.getheaders())
        raw_body = res.read().decode("utf-8")
        conn.close()

        try:
            data = json.loads(raw_body)
        except Exception:
            data = {}

        return status, data, resp_headers, raw_body

    def test_swagger_ui_dashboard_endpoint(self):
        status, _, headers, raw = self._make_request("GET", "/api/docs")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn("<title>FinansProtect API Documentation</title>", raw)
        self.assertIn("swagger-ui", raw)

    def test_openapi_json_endpoint(self):
        status, data, headers, _ = self._make_request("GET", "/api/openapi.json")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        self.assertEqual(data.get("openapi"), "3.1.0")

    def test_openapi_yaml_endpoint(self):
        status, _, headers, raw = self._make_request("GET", "/api/openapi.yaml")
        self.assertEqual(status, 200)
        self.assertIn("text/yaml", headers.get("Content-Type", ""))
        self.assertIn("openapi: 3.1.0", raw)

    def test_v2_telemetry_endpoint(self):
        status, data, _, _ = self._make_request("GET", "/api/v2/telemetry")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("api_version"), "2.0.0")
        self.assertIn("pqc_nodes_online", data)

    def test_v1_post_validation_success(self):
        valid_correction = {
            "discrepancy_id": "DISC_BG_001",
            "resolution": "RESOLVED_MANUAL_AUDIT",
            "auditor": "Senior CPA Auditor",
        }
        status, data, _, _ = self._make_request("POST", "/api/v1/compliance/correct", valid_correction)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))

    def test_v1_post_validation_failure_schema_error(self):
        invalid_correction = {
            "resolution": "RESOLVED_MANUAL_AUDIT"
        }
        status, data, _, _ = self._make_request("POST", "/api/v1/compliance/correct", invalid_correction)
        self.assertEqual(status, 400)
        self.assertEqual(data.get("error"), "SCHEMA_VALIDATION_ERROR")
        self.assertIn("Missing required property 'discrepancy_id'", data.get("message", ""))


if __name__ == "__main__":
    unittest.main()
