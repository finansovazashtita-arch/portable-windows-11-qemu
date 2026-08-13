"""
Unit tests for Autonomous Enterprise Inventory & Stock Valuation Engine.
"""

import unittest

from src.accounting.inventory_valuation import InventoryValuationEngine, ValuationMethod


class TestInventoryValuationEngine(unittest.TestCase):
    """Test suite for InventoryValuationEngine."""

    def setUp(self):
        self.engine = InventoryValuationEngine()

    def test_fifo_cogs_writeoff(self):
        # Batch 1: 10 units @ €10.00
        self.engine.add_inventory_receipt(sku="LAPTOP_X1", quantity=10, unit_cost_eur=10.0)
        # Batch 2: 10 units @ €15.00
        self.engine.add_inventory_receipt(sku="LAPTOP_X1", quantity=10, unit_cost_eur=15.0)

        # Sell 12 units under FIFO: 10 * 10 + 2 * 15 = €130.00
        cogs, entries = self.engine.calculate_cogs_writeoff("LAPTOP_X1", quantity_sold=12, method=ValuationMethod.FIFO)

        self.assertEqual(cogs, 130.0)
        self.assertEqual(entries[0]["debit_account"], "702")
        self.assertEqual(entries[0]["credit_account"], "304")

    def test_weighted_average_cogs_writeoff(self):
        self.engine.add_inventory_receipt(sku="MOUSE_M1", quantity=10, unit_cost_eur=10.0)
        self.engine.add_inventory_receipt(sku="MOUSE_M1", quantity=10, unit_cost_eur=20.0)

        # Total 20 units @ avg €15.00. Sell 5 units -> €75.00
        cogs, _ = self.engine.calculate_cogs_writeoff("MOUSE_M1", quantity_sold=5, method=ValuationMethod.WEIGHTED_AVERAGE)

        self.assertEqual(cogs, 75.0)

    def test_inventory_scrap_writeoff(self):
        self.engine.add_inventory_receipt(sku="MONITOR_M2", quantity=5, unit_cost_eur=100.0)
        entries = self.engine.writeoff_scrapped_inventory("MONITOR_M2", quantity_scrapped=1, reason_bg="Счупен дисплей")

        self.assertEqual(entries[0]["debit_account"], "601")
        self.assertEqual(entries[0]["credit_account"], "304")
        self.assertEqual(entries[0]["amount_eur"], 100.0)


if __name__ == "__main__":
    unittest.main()
