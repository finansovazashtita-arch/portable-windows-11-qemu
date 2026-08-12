"""
Unit tests for Prometheus & Grafana Monitoring Telemetry Exporter Engine.
"""

import unittest

from src.dashboard.prometheus_exporter import PrometheusTelemetryExporter


class TestPrometheusTelemetryExporter(unittest.TestCase):
    """Test suite for PrometheusTelemetryExporter."""

    def setUp(self):
        self.exporter = PrometheusTelemetryExporter()

    def test_record_turnover(self):
        self.exporter.record_turnover(15000.50, 10)
        metrics = self.exporter.generate_prometheus_metrics()

        self.assertIn("financial_processed_turnover_eur_total 15000.50", metrics)
        self.assertIn("financial_transactions_processed_total 10", metrics)

    def test_update_gauges(self):
        self.exporter.update_qemu_ram(8192 * 1024 * 1024)
        self.exporter.update_ocr_accuracy(0.9995)
        self.exporter.set_cluster_leader(False)

        metrics = self.exporter.generate_prometheus_metrics()
        self.assertIn("qemu_vm_ram_bytes 8589934592", metrics)
        self.assertIn("ocr_accuracy_ratio 0.9995", metrics)
        self.assertIn("ha_cluster_leader_status 0", metrics)


if __name__ == "__main__":
    unittest.main()
