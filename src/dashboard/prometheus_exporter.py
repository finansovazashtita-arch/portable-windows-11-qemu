"""
Prometheus & Grafana Monitoring Telemetry Exporter Engine.

Exposes real-time Prometheus /metrics endpoint payload for Grafana dashboards monitoring:
- Processed Financial Turnover Total (€)
- Processed Transaction Counter
- OCR Extraction Precision Ratio (%)
- QEMU Windows 11 VM RAM Memory Allocation (Bytes)
- High Availability (HA) Leader Status (1=Primary, 0=Secondary)
"""

import logging
from typing import Any, Dict

logger = logging.getLogger("prometheus_exporter")


class PrometheusTelemetryExporter:
    """Exporter rendering standard Prometheus format metrics payload."""

    def __init__(self):
        self.total_turnover_eur: float = 0.0
        self.total_transactions_count: int = 0
        self.ocr_accuracy_ratio: float = 0.999
        self.qemu_vm_ram_bytes: int = 4096 * 1024 * 1024  # Default 4GB RAM
        self.is_cluster_leader: int = 1

    def record_turnover(self, amount_eur: float, tx_count: int = 1):
        """Increments turnover and transaction count metrics."""
        self.total_turnover_eur += amount_eur
        self.total_transactions_count += tx_count

    def update_qemu_ram(self, ram_bytes: int):
        """Updates QEMU VM RAM allocation gauge."""
        self.qemu_vm_ram_bytes = ram_bytes

    def update_ocr_accuracy(self, accuracy_ratio: float):
        """Updates OCR accuracy gauge (0.0 to 1.0)."""
        self.ocr_accuracy_ratio = accuracy_ratio

    def set_cluster_leader(self, is_leader: bool):
        """Updates HA cluster leader status gauge."""
        self.is_cluster_leader = 1 if is_leader else 0

    def generate_prometheus_metrics(self) -> str:
        """Renders standard Prometheus exposition text format."""
        metrics_lines = [
            "# HELP financial_processed_turnover_eur_total Total processed turnover in EUR.",
            "# TYPE financial_processed_turnover_eur_total counter",
            f"financial_processed_turnover_eur_total {self.total_turnover_eur:.2f}",
            "",
            "# HELP financial_transactions_processed_total Total count of processed bank statement transactions.",
            "# TYPE financial_transactions_processed_total counter",
            f"financial_transactions_processed_total {self.total_transactions_count}",
            "",
            "# HELP ocr_accuracy_ratio OCR extraction accuracy ratio (0.0 - 1.0).",
            "# TYPE ocr_accuracy_ratio gauge",
            f"ocr_accuracy_ratio {self.ocr_accuracy_ratio:.4f}",
            "",
            "# HELP qemu_vm_ram_bytes QEMU Windows 11 VM RAM memory allocation in bytes.",
            "# TYPE qemu_vm_ram_bytes gauge",
            f"qemu_vm_ram_bytes {self.qemu_vm_ram_bytes}",
            "",
            "# HELP ha_cluster_leader_status High Availability cluster leader status (1=Leader, 0=Standby).",
            "# TYPE ha_cluster_leader_status gauge",
            f"ha_cluster_leader_status {self.is_cluster_leader}",
        ]
        return "\n".join(metrics_lines)
