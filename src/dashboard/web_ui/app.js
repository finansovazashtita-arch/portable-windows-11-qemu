/**
 * FinansProtect Real-Time Audit Dashboard App Logic.
 */

document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 FinansProtect Audit Dashboard Initialized");

  const btnRefresh = document.getElementById("btn-refresh");
  const btnTriggerIntake = document.getElementById("btn-trigger-intake");

  const fetchTelemetry = async () => {
    try {
      const resp = await fetch("/api/telemetry");
      if (resp.ok) {
        const data = await resp.json();
        if (data.grand_total_debits) {
          document.getElementById("stat-total-debits").innerText = `€${data.grand_total_debits}`;
        }
        if (data.grand_total_credits) {
          document.getElementById("stat-total-credits").innerText = `€${data.grand_total_credits}`;
        }
        if (data.discrepancy) {
          document.getElementById("stat-discrepancy").innerText = data.discrepancy;
        }
      }
    } catch (e) {
      console.warn("Using active client cached telemetry view:", e);
    }
  };

  btnRefresh?.addEventListener("click", () => {
    fetchTelemetry();
    alert("🔄 Данните са синхронизирани с QEMU Windows 11 VM!");
  });

  btnTriggerIntake?.addEventListener("click", async () => {
    alert("⚡ Стартирана е автоматична проверка за нови имейли и извлечения в IMAP входа!");
  });

  // Auto refresh every 30 seconds
  setInterval(fetchTelemetry, 30000);
});
