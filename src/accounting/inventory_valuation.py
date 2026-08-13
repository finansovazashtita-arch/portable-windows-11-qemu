"""
Autonomous Enterprise Inventory & Stock Valuation Engine (FIFO / Weighted Average).

Handles double-entry accounting for inventory valuation and stock movements:
- Receipt of goods / inventory stock (Account 304 "Стоки" / Account 401 "Доставчици")
- Cost of Goods Sold (COGS) write-off (Account 702 / Account 304) via FIFO or Weighted Average
- Inventory scrap / damage write-off (Account 601 / Account 304)
"""

import dataclasses
import enum
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("inventory_valuation")


class ValuationMethod(str, enum.Enum):
    FIFO = "FIFO"
    WEIGHTED_AVERAGE = "WEIGHTED_AVERAGE"


@dataclasses.dataclass
class InventoryItemBatch:
    """Dataclass holding inventory batch details for valuation."""

    batch_id: str
    sku: str
    quantity: float
    unit_cost_eur: float


class InventoryValuationEngine:
    """Engine managing inventory valuation and double-entry stock write-offs."""

    def __init__(self) -> None:
        self.inventory_batches: Dict[str, List[InventoryItemBatch]] = {}

    def add_inventory_receipt(
        self, sku: str, quantity: float, unit_cost_eur: float, batch_id: Optional[str] = None
    ) -> InventoryItemBatch:
        """Records receipt of inventory items (Debit 304 / Credit 401)."""
        b_id = batch_id or f"BATCH_{int(time.time() * 1000)}"
        batch = InventoryItemBatch(
            batch_id=b_id,
            sku=sku.upper(),
            quantity=quantity,
            unit_cost_eur=unit_cost_eur,
        )

        if batch.sku not in self.inventory_batches:
            self.inventory_batches[batch.sku] = []

        self.inventory_batches[batch.sku].append(batch)
        logger.info(f"📦 Inventory Receipt: SKU={batch.sku}, Qty={quantity}, UnitCost={unit_cost_eur:.2f} EUR")
        return batch

    def calculate_cogs_writeoff(
        self, sku: str, quantity_sold: float, method: ValuationMethod = ValuationMethod.FIFO
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Calculates COGS cost using FIFO or Weighted Average method and generates journal entries."""
        sku_clean = sku.upper()
        batches = self.inventory_batches.get(sku_clean, [])

        if not batches or sum(b.quantity for b in batches) < quantity_sold:
            raise ValueError(f"Insufficient stock for SKU {sku_clean} to sell {quantity_sold} units.")

        total_cogs = 0.0
        remaining_to_sell = quantity_sold

        if method == ValuationMethod.FIFO:
            for b in list(batches):
                if remaining_to_sell <= 0:
                    break
                qty_from_batch = min(b.quantity, remaining_to_sell)
                cogs_part = qty_from_batch * b.unit_cost_eur
                total_cogs += cogs_part

                b.quantity -= qty_from_batch
                remaining_to_sell -= qty_from_batch

                if b.quantity <= 0:
                    batches.remove(b)

        else:  # WEIGHTED_AVERAGE
            total_qty = sum(b.quantity for b in batches)
            total_val = sum(b.quantity * b.unit_cost_eur for b in batches)
            avg_unit_cost = total_val / total_qty
            total_cogs = round(quantity_sold * avg_unit_cost, 2)

            for b in list(batches):
                qty_deduct = (b.quantity / total_qty) * quantity_sold
                b.quantity -= qty_deduct
                if b.quantity <= 0:
                    batches.remove(b)

        total_cogs = round(total_cogs, 2)
        entries = [
            {
                "document_number": f"COGS_{sku_clean}",
                "debit_account": "702",  # Cost of Goods Sold / Отписване на продадени стоки
                "credit_account": "304",  # Goods Inventory / Стоки
                "amount_eur": total_cogs,
                "narrative": f"Изписване на себестойност ({method.value}) за {quantity_sold} бр. {sku_clean}",
            }
        ]
        logger.info(f"🏷️ COGS Write-off ({method.value}): SKU={sku_clean}, Qty={quantity_sold}, Total COGS={total_cogs:.2f} EUR")
        return total_cogs, entries

    def writeoff_scrapped_inventory(
        self, sku: str, quantity_scrapped: float, reason_bg: str = "Брак на повредени стоки"
    ) -> List[Dict[str, Any]]:
        """Handles inventory scrap write-offs (Debit 601 / Credit 304)."""
        cogs, _ = self.calculate_cogs_writeoff(sku, quantity_scrapped, ValuationMethod.FIFO)

        entries = [
            {
                "document_number": f"SCRAP_{sku.upper()}",
                "debit_account": "601",  # Materials/Inventory Scrap / Разходи за брак
                "credit_account": "304",  # Goods Inventory / Стоки
                "amount_eur": cogs,
                "narrative": f"Брак на стока {sku.upper()} ({reason_bg})",
            }
        ]
        logger.info(f"🗑️ Inventory Scrap Write-off: SKU={sku.upper()}, Qty={quantity_scrapped}, Loss={cogs:.2f} EUR")
        return entries
