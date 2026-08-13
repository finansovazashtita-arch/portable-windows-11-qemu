"""
Unit tests for Automated Fixed Assets & Depreciation Schedule Manager.
"""

import unittest

from src.accounting.fixed_assets_depreciation import CITATaxCategory, FixedAssetsDepreciationEngine


class TestFixedAssetsDepreciationEngine(unittest.TestCase):
    """Test suite for FixedAssetsDepreciationEngine."""

    def test_register_fixed_asset(self):
        asset = FixedAssetsDepreciationEngine.register_fixed_asset(
            asset_id="AST_001",
            name="Лаптоп Dell XPS",
            acquisition_cost_eur=1200.0,
            tax_category=CITATaxCategory.CAT_IV,
        )

        self.assertEqual(asset.asset_id, "AST_001")
        self.assertEqual(asset.tax_category, CITATaxCategory.CAT_IV)
        self.assertEqual(asset.book_value_eur, 1200.0)

    def test_calculate_monthly_depreciation_cat_iv(self):
        # Category IV is 50% annual -> €1200 * 0.50 / 12 = €50.00/month
        asset = FixedAssetsDepreciationEngine.register_fixed_asset(
            asset_id="AST_002",
            name="Сървър HP ProLiant",
            acquisition_cost_eur=1200.0,
            tax_category=CITATaxCategory.CAT_IV,
        )
        monthly_dep = FixedAssetsDepreciationEngine.calculate_monthly_depreciation(asset)
        self.assertEqual(monthly_dep, 50.0)

    def test_generate_monthly_depreciation_entries(self):
        asset = FixedAssetsDepreciationEngine.register_fixed_asset(
            asset_id="AST_003",
            name="Фирмен Автомобил",
            acquisition_cost_eur=24000.0,
            tax_category=CITATaxCategory.CAT_V,  # 25% annual -> €500/month
        )

        entries = FixedAssetsDepreciationEngine.generate_monthly_depreciation_entries([asset], month_str="2026-01")

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["debit_account"], "603")
        self.assertEqual(entries[0]["credit_account"], "241")
        self.assertEqual(entries[0]["amount_eur"], 500.0)
        self.assertEqual(asset.accumulated_depreciation_eur, 500.0)
        self.assertEqual(asset.book_value_eur, 23500.0)


if __name__ == "__main__":
    unittest.main()
