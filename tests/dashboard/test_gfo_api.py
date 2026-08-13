"""
Unit and Integration Tests for GFO REST API Endpoints in FinansProtect Dashboard Server.
"""

import json
import pytest
from src.accounting.gfo_generator import CompanyEntityProfile, GFOGeneratorEngine


class TestGFOApiEndpoints:

    def test_gfo_generate_payload(self):
        profile = CompanyEntityProfile(
            company_name="АПИ ТЕСТ ЕООД",
            eik="987654321",
            address="гр. Пловдив",
            manager_name="Петър Петров",
        )
        tb = {
            "101": {"final_credit": 1000.0},
            "503": {"final_debit": 1000.0},
        }
        report = GFOGeneratorEngine.generate_gfo(profile, tb, 2025)
        canonical = GFOGeneratorEngine.export_canonical_json(report)

        assert canonical["report_id"] == "GFO-987654321-2025"
        assert canonical["company_profile"]["company_name"] == "АПИ ТЕСТ ЕООД"
        assert canonical["balance_sheet"]["assets"]["cash_and_cash_equivalents"] == 1000.0
