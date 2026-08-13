"""
Automated Fixed Assets & Depreciation Schedule Manager (PPE / Intangible Assets).

Manages Bulgarian Property, Plant & Equipment (PPE) assets and CITA (ЗКПО) tax depreciation:
- CITA Tax Categories I - VII (Buildings 4%, Machinery 30%, IT/Software 50%, Cars 25%, etc.)
- Fixed asset acquisition (Account 204 "Машини и съоръжения" / Account 401 "Доставчици")
- Monthly linear depreciation calculation (Debit 603 "Разходи за амортизация" / Credit 241 "Амортизация на ДМА")
"""

import dataclasses
import enum
import logging
from typing import Any, Dict, List

logger = logging.getLogger("fixed_assets_depreciation")


class CITATaxCategory(str, enum.Enum):
    CAT_I = "CAT_I"  # Buildings, structures: 4%
    CAT_II = "CAT_II"  # Machinery, equipment, apparatus: 30%
    CAT_III = "CAT_III"  # Transport vehicles (excluding cars): 15%
    CAT_IV = "CAT_IV"  # Computers, software, hardware, peripheral IT: 50%
    CAT_V = "CAT_V"  # Automobiles: 25%
    CAT_VI = "CAT_VI"  # Assets with limited life by contract
    CAT_VII = "CAT_VII"  # All other depreciable assets: 15%


CITA_ANNUAL_RATES = {
    CITATaxCategory.CAT_I: 4.0,
    CITATaxCategory.CAT_II: 30.0,
    CITATaxCategory.CAT_III: 15.0,
    CITATaxCategory.CAT_IV: 50.0,
    CITATaxCategory.CAT_V: 25.0,
    CITATaxCategory.CAT_VI: 10.0,
    CITATaxCategory.CAT_VII: 15.0,
}


@dataclasses.dataclass
class FixedAsset:
    """Dataclass holding tangible fixed asset details."""

    asset_id: str
    name: str
    acquisition_cost_eur: float
    tax_category: CITATaxCategory
    acquisition_date: str
    accumulated_depreciation_eur: float = 0.0

    @property
    def book_value_eur(self) -> float:
        return max(0.0, round(self.acquisition_cost_eur - self.accumulated_depreciation_eur, 2))


class FixedAssetsDepreciationEngine:
    """Engine managing fixed assets register and generating monthly depreciation entries."""

    @classmethod
    def register_fixed_asset(
        cls,
        asset_id: str,
        name: str,
        acquisition_cost_eur: float,
        tax_category: CITATaxCategory,
        acquisition_date: str = "2026-01-01",
    ) -> FixedAsset:
        """Registers a new fixed asset in the company register."""
        asset = FixedAsset(
            asset_id=asset_id,
            name=name,
            acquisition_cost_eur=acquisition_cost_eur,
            tax_category=tax_category,
            acquisition_date=acquisition_date,
        )
        logger.info(f"🏗️ Registered Fixed Asset [{asset_id}]: '{name}' ({tax_category.value}) = €{acquisition_cost_eur:,.2f}")
        return asset

    @classmethod
    def calculate_monthly_depreciation(cls, asset: FixedAsset) -> float:
        """Calculates monthly linear depreciation amount based on CITA tax rate."""
        annual_rate = CITA_ANNUAL_RATES.get(asset.tax_category, 15.0)
        annual_depreciation = asset.acquisition_cost_eur * (annual_rate / 100.0)
        monthly_depreciation = round(annual_depreciation / 12.0, 2)

        # Cap at remaining book value
        return min(monthly_depreciation, asset.book_value_eur)

    @classmethod
    def generate_monthly_depreciation_entries(
        cls, assets: List[FixedAsset], month_str: str = "2026-01"
    ) -> List[Dict[str, Any]]:
        """Generates monthly double-entry depreciation journal entries (Debit 603 / Credit 241)."""
        entries = []
        for asset in assets:
            monthly_dep = cls.calculate_monthly_depreciation(asset)
            if monthly_dep <= 0:
                continue

            asset.accumulated_depreciation_eur = round(asset.accumulated_depreciation_eur + monthly_dep, 2)
            entries.append(
                {
                    "date": f"{month_str}-31",
                    "document_number": f"DEP_{asset.asset_id}_{month_str}",
                    "narrative": f"Месечна амортизация на {asset.name} (Категория {asset.tax_category.value})",
                    "debit_account": "603",  # Depreciation expense / Разходи за амортизация
                    "debit_name": "Разходи за амортизация",
                    "credit_account": "241",  # Accumulated PPE depreciation / Амортизация на ДМА
                    "credit_name": "Амортизация на ДМА",
                    "amount_eur": monthly_dep,
                }
            )
            logger.info(f"📈 Monthly Depreciation [{asset.asset_id}]: €{monthly_dep:,.2f} (Book value: €{asset.book_value_eur:,.2f})")
        return entries
