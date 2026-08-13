"""
Unit & Integration Tests for Schema Manager & Database Isolation (M75).
"""

import sqlite3
import pytest
from src.billing.schema_manager import SchemaManager


class TestSchemaManager:

    @pytest.fixture
    def schema_mgr(self, tmp_path):
        db_file = str(tmp_path / "test_schemas.db")
        return SchemaManager(db_path=db_file)

    def test_sanitize_tenant_id(self):
        clean = SchemaManager.sanitize_tenant_id("t_12345-abc!")
        assert clean == "t_12345_abc_"

    def test_provision_tenant_schema(self, schema_mgr):
        schema_name = schema_mgr.provision_tenant_schema("tenant_test_101")
        assert schema_name.startswith("tenant_schema_")

        info = schema_mgr.get_schema_info("tenant_test_101")
        assert info["provisioned"] is True
        assert info["status"] == "PROVISIONED"
        assert len(info["table_row_counts"]) == 4

    def test_drop_tenant_schema(self, schema_mgr):
        schema_mgr.provision_tenant_schema("tenant_test_202")
        info1 = schema_mgr.get_schema_info("tenant_test_202")
        assert info1["provisioned"] is True

        dropped = schema_mgr.drop_tenant_schema("tenant_test_202")
        assert dropped is True

        info2 = schema_mgr.get_schema_info("tenant_test_202")
        assert info2["provisioned"] is False
