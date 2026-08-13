"""
Multi-Dimensional Analytics Query Builder Module (Milestone M76).

Enables flexible OLAP aggregation queries over financial transactions,
journal entries, invoice line items, and multi-tenant usage metrics.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable


class AggregationMetric:
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    VARIANCE = "variance"
    PCT_TOTAL = "pct_total"


@dataclass
class QueryFilter:
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    tenant_id: Optional[str] = None
    counterparties: List[str] = field(default_factory=list)
    account_codes: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    cost_centers: List[str] = field(default_factory=list)
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: Optional[str] = None
    search_query: Optional[str] = None


@dataclass
class QueryResult:
    dimensions: List[str]
    metrics: List[str]
    data: List[Dict[str, Any]]
    total_records: int
    summary_totals: Dict[str, float]


class AnalyticsQueryBuilder:
    """Multi-dimensional OLAP aggregation engine for financial records."""

    def __init__(self, data_source: Optional[List[Dict[str, Any]]] = None):
        self.raw_data: List[Dict[str, Any]] = data_source or []

    def set_data_source(self, data_source: List[Dict[str, Any]]) -> "AnalyticsQueryBuilder":
        self.raw_data = data_source
        return self

    def execute_query(
        self,
        filters: Optional[QueryFilter] = None,
        group_by: Optional[List[str]] = None,
        metrics: Optional[List[Dict[str, str]]] = None,
        order_by: Optional[str] = None,
        ascending: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> QueryResult:
        """
        Execute an OLAP aggregation query.
        
        `metrics`: list of dicts like `[{"field": "amount", "agg": "sum", "alias": "total_amount"}]`
        """
        filters = filters or QueryFilter()
        group_by = group_by or []
        metrics = metrics or [{"field": "amount", "agg": AggregationMetric.SUM, "alias": "sum_amount"}]

        filtered = self._apply_filters(self.raw_data, filters)
        aggregated = self._aggregate(filtered, group_by, metrics)

        # Sort
        if order_by and aggregated:
            aggregated.sort(key=lambda r: r.get(order_by, 0), reverse=not ascending)

        # Summary totals
        summary_totals = self._compute_summary_totals(filtered, metrics)

        # Paginate
        paginated = aggregated[offset : offset + limit] if limit > 0 else aggregated

        return QueryResult(
            dimensions=group_by,
            metrics=[m.get("alias", f"{m['agg']}_{m['field']}") for m in metrics],
            data=paginated,
            total_records=len(aggregated),
            summary_totals=summary_totals,
        )

    def _apply_filters(self, records: List[Dict[str, Any]], filters: QueryFilter) -> List[Dict[str, Any]]:
        result = []
        for r in records:
            # Date filtering
            date_val = r.get("date") or r.get("created_at") or r.get("timestamp")
            if filters.start_date and date_val:
                if str(date_val) < filters.start_date:
                    continue
            if filters.end_date and date_val:
                if str(date_val) > filters.end_date:
                    continue

            # Tenant
            if filters.tenant_id and r.get("tenant_id") and r.get("tenant_id") != filters.tenant_id:
                continue

            # Counterparty
            if filters.counterparties:
                cp = r.get("counterparty") or r.get("partner_name") or r.get("counterparty_name")
                if cp not in filters.counterparties:
                    continue

            # Account Codes
            if filters.account_codes:
                acc = r.get("account_code") or r.get("account") or r.get("debit_account") or r.get("credit_account")
                if acc not in filters.account_codes:
                    continue

            # Categories
            if filters.categories:
                cat = r.get("category") or r.get("tax_category")
                if cat not in filters.categories:
                    continue

            # Cost Centers
            if filters.cost_centers:
                cc = r.get("cost_center")
                if cc not in filters.cost_centers:
                    continue

            # Currency
            if filters.currency:
                curr = r.get("currency", "BGN")
                if curr != filters.currency:
                    continue

            # Amount thresholds
            amt = float(r.get("amount", r.get("debit", r.get("credit", 0.0))))
            if filters.min_amount is not None and amt < filters.min_amount:
                continue
            if filters.max_amount is not None and amt > filters.max_amount:
                continue

            # Search text query
            if filters.search_query:
                q = filters.search_query.lower()
                narrative = str(r.get("narrative", "") or r.get("description", "")).lower()
                cp = str(r.get("counterparty", "")).lower()
                doc = str(r.get("doc_number", "")).lower()
                if q not in narrative and q not in cp and q not in doc:
                    continue

            result.append(r)
        return result

    def _aggregate(
        self,
        records: List[Dict[str, Any]],
        group_by: List[str],
        metrics: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        if not group_by:
            # Single aggregate bucket
            bucket = {"_all_": True}
            for m in metrics:
                alias = m.get("alias", f"{m['agg']}_{m['field']}")
                bucket[alias] = self._calc_metric(records, m["field"], m["agg"])
            return [bucket]

        groups: Dict[tuple, List[Dict[str, Any]]] = {}
        for r in records:
            key_parts = []
            for dim in group_by:
                val = self._extract_dimension_val(r, dim)
                key_parts.append(val)
            group_key = tuple(key_parts)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(r)

        result = []
        for group_key, recs in groups.items():
            row = {}
            for idx, dim in enumerate(group_by):
                row[dim] = group_key[idx]

            for m in metrics:
                alias = m.get("alias", f"{m['agg']}_{m['field']}")
                row[alias] = self._calc_metric(recs, m["field"], m["agg"])

            result.append(row)
        return result

    def _extract_dimension_val(self, record: Dict[str, Any], dimension: str) -> str:
        if dimension == "period" or dimension == "month":
            dt = record.get("date") or record.get("created_at") or ""
            return str(dt)[:7] if len(str(dt)) >= 7 else "Unknown"
        elif dimension == "year":
            dt = record.get("date") or record.get("created_at") or ""
            return str(dt)[:4] if len(str(dt)) >= 4 else "Unknown"
        elif dimension == "day":
            dt = record.get("date") or record.get("created_at") or ""
            return str(dt)[:10] if len(str(dt)) >= 10 else "Unknown"
        elif dimension in record:
            return str(record[dimension])
        else:
            # Fallbacks
            if dimension == "counterparty":
                return str(record.get("partner_name", record.get("counterparty_name", "Unknown")))
            elif dimension == "account_code":
                return str(record.get("account", record.get("debit_account", "Unknown")))
            return "Unknown"

    def _calc_metric(self, records: List[Dict[str, Any]], field_name: str, agg: str) -> float:
        values = []
        for r in records:
            v = r.get(field_name)
            if v is not None:
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    pass

        if not values:
            return 0.0

        if agg == AggregationMetric.SUM:
            return round(sum(values), 2)
        elif agg == AggregationMetric.AVG:
            return round(sum(values) / len(values), 2)
        elif agg == AggregationMetric.MIN:
            return round(min(values), 2)
        elif agg == AggregationMetric.MAX:
            return round(max(values), 2)
        elif agg == AggregationMetric.COUNT:
            return float(len(values))
        elif agg == AggregationMetric.VARIANCE:
            avg = sum(values) / len(values)
            var = sum((x - avg) ** 2 for x in values) / len(values)
            return round(var, 2)
        return round(sum(values), 2)

    def _compute_summary_totals(
        self, records: List[Dict[str, Any]], metrics: List[Dict[str, str]]
    ) -> Dict[str, float]:
        totals = {}
        for m in metrics:
            alias = m.get("alias", f"{m['agg']}_{m['field']}")
            totals[alias] = self._calc_metric(records, m["field"], m["agg"])
        return totals
