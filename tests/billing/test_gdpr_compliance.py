"""
Unit & Integration Tests for GDPR Article 17 Right-to-Erasure Protocol (M75).
"""

import os
import pytest
from src.billing.gdpr_compliance import GDPRComplianceManager, ErasureCertificate
from src.billing.tenant_manager import TenantManager


class TestGDPRComplianceManager:

    @pytest.fixture
    def gdpr_setup(self, tmp_path):
        db_file = str(tmp_path / "gdpr_test.db")
        storage_dir = str(tmp_path / "tenants_storage")

        tenant_mgr = TenantManager(db_path=db_file)
        tenant = tenant_mgr.create_tenant("Test GDPR Ltd", "999888777", "gdpr@test.bg")

        # Create dummy file in storage
        t_dir = os.path.join(storage_dir, tenant.tenant_id)
        os.makedirs(t_dir, exist_ok=True)
        with open(os.path.join(t_dir, "statement_001.pdf"), "w") as f:
            f.write("DUMMY PDF CONTENT")

        gdpr_mgr = GDPRComplianceManager(
            schema_manager=tenant_mgr.schema_manager,
            metering_engine=tenant_mgr.metering_engine,
            db_path=db_file,
            storage_dir=storage_dir,
        )

        return gdpr_mgr, tenant, tenant_mgr, t_dir

    def test_execute_right_to_erasure(self, gdpr_setup):
        gdpr_mgr, tenant, tenant_mgr, t_dir = gdpr_setup

        cert = gdpr_mgr.execute_right_to_erasure(
            tenant_id=tenant.tenant_id,
            requested_by="DPO_OFFICER",
            reason="CLIENT_CONTRACT_TERMINATION",
        )

        assert isinstance(cert, ErasureCertificate)
        assert cert.tenant_id == tenant.tenant_id
        assert cert.verification_hash is not None
        assert len(cert.verification_hash) == 64
        assert not os.path.exists(t_dir)

        # Check stored certificate
        stored_cert = gdpr_mgr.get_erasure_certificate(cert.request_id)
        assert stored_cert is not None
        assert stored_cert.verification_hash == cert.verification_hash
