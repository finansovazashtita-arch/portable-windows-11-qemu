/**
 * FinansProtect Real-Time Audit Compliance & WebSockets Telemetry App (M65).
 */

document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 FinansProtect M65 Web UI WebSockets Dashboard Initialized");

  // State
  let telemetryData = null;
  let activeEntityFilter = "ALL";
  let wsSocket = null;
  let reconnectTimer = null;

  // DOM Elements
  const wsIndicatorDot = document.getElementById("ws-indicator-dot");
  const wsStatusText = document.getElementById("ws-status-text");
  const wsMetaLatency = document.getElementById("ws-meta-latency");

  const statTotalDebits = document.getElementById("stat-total-debits");
  const statTotalCredits = document.getElementById("stat-total-credits");
  const statDiscrepancy = document.getElementById("stat-discrepancy");
  const statDiscrepancyBadge = document.getElementById("stat-discrepancy-badge");
  const statSha256 = document.getElementById("stat-sha256");

  const entitiesTbody = document.getElementById("entities-tbody");
  const einvoicesTbody = document.getElementById("einvoices-tbody");
  const einvoiceStreamCount = document.getElementById("einvoice-stream-count");
  const pqcNodesContainer = document.getElementById("pqc-nodes-container");
  const flaggedEntriesTbody = document.getElementById("flagged-entries-tbody");
  const correctionsLedgerTbody = document.getElementById("corrections-ledger-tbody");
  const smartReconcileTbody = document.getElementById("smart-reconcile-tbody");
  const smartMatchCountBadge = document.getElementById("smart-match-count-badge");
  const flaggedCountBadge = document.getElementById("flagged-count-badge");
  const overallComplianceBadge = document.getElementById("overall-compliance-badge");

  // Action Buttons
  const btnTriggerEinvoice = document.getElementById("btn-trigger-einvoice");
  const btnSyncMesh = document.getElementById("btn-sync-mesh");
  const btnOpenCorrectionModal = document.getElementById("btn-open-correction-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const btnCancelModal = document.getElementById("btn-cancel-modal");
  const correctionModal = document.getElementById("correction-modal");
  const correctionForm = document.getElementById("correction-form");

  // Entity Tabs
  const entityTabsContainer = document.getElementById("entity-tabs");

  // --- WebSockets Connection Management ---
  const connectWebSocket = () => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host || "localhost:8095";
    const wsUrl = `${protocol}//${host}/ws`;

    console.log(`📡 Connecting WebSockets telemetry to ${wsUrl}...`);

    try {
      wsSocket = new WebSocket(wsUrl);

      wsSocket.onopen = () => {
        console.log("✅ WebSockets Stream Connected!");
        if (wsIndicatorDot) wsIndicatorDot.className = "ws-dot pulse-online";
        if (wsStatusText) wsStatusText.innerText = "WebSockets: LIVE STREAM";
        if (wsMetaLatency) wsMetaLatency.innerText = "Лаг: 1.2 ms | Chained SHA-256";
        if (reconnectTimer) {
          clearTimeout(reconnectTimer);
          reconnectTimer = null;
        }
      };

      wsSocket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.entities || payload.summary) {
            telemetryData = payload;
            renderDashboard(payload);
          }
        } catch (err) {
          console.warn("Failed to parse WS payload:", err);
        }
      };

      wsSocket.onerror = (err) => {
        console.warn("WebSocket error observed, falling back to REST:", err);
        fetchTelemetryREST();
      };

      wsSocket.onclose = () => {
        console.log("🔌 WebSockets Stream Disconnected. Reconnecting in 3s...");
        if (wsIndicatorDot) wsIndicatorDot.className = "ws-dot pulse-reconnecting";
        if (wsStatusText) wsStatusText.innerText = "WebSockets: REST FALLBACK";
        fetchTelemetryREST();
        reconnectTimer = setTimeout(connectWebSocket, 3000);
      };
    } catch (e) {
      console.warn("WebSocket construction failed, using REST polling fallback:", e);
      fetchTelemetryREST();
    }
  };

  // REST API Fallback
  const fetchTelemetryREST = async () => {
    try {
      const resp = await fetch("/api/compliance/telemetry");
      if (resp.ok) {
        const data = await resp.json();
        telemetryData = data;
        renderDashboard(data);
      }
    } catch (e) {
      console.warn("REST Telemetry fetch error:", e);
    }
  };

  // --- Dashboard Renderer ---
  const renderDashboard = (data) => {
    if (!data) return;

    // 1. Top Summary Stats
    if (data.summary) {
      if (statTotalDebits) statTotalDebits.innerText = `€${data.summary.grand_total_debits_eur.toLocaleString()}`;
      if (statTotalCredits) statTotalCredits.innerText = `€${data.summary.grand_total_credits_eur.toLocaleString()}`;

      const disc = data.summary.grand_total_discrepancy_eur;
      if (statDiscrepancy) {
        statDiscrepancy.innerText = `€${disc.toFixed(2)}`;
        if (disc === 0) {
          statDiscrepancy.className = "stat-value";
          if (statDiscrepancyBadge) {
            statDiscrepancyBadge.innerText = "PASSED (0.00 EUR разхождение)";
            statDiscrepancyBadge.className = "stat-footer positive";
          }
        } else {
          statDiscrepancy.className = "stat-value text-alert";
          if (statDiscrepancyBadge) {
            statDiscrepancyBadge.innerText = `FLAGGED (${data.flagged_entries?.length || 1} корекция чака)`;
            statDiscrepancyBadge.className = "stat-footer badge-warning";
          }
        }
      }

      if (statSha256 && data.summary.audit_ledger_hash_head) {
        const hash = data.summary.audit_ledger_hash_head;
        statSha256.innerText = `${hash.substring(0, 8)}...${hash.substring(hash.length - 8)}`;
      }
    }

    if (data.overall_compliance_score !== undefined && overallComplianceBadge) {
      overallComplianceBadge.innerText = `Compliance: ${data.overall_compliance_score}%`;
      overallComplianceBadge.className = data.overall_compliance_score === 100 ? "badge badge-success" : "badge badge-warning";
    }

    // 2. Render Multi-Entity Audit Compliance Table
    if (data.entities && entitiesTbody) {
      const filtered = activeEntityFilter === "ALL" 
        ? data.entities 
        : data.entities.filter(e => e.entity_id === activeEntityFilter);

      entitiesTbody.innerHTML = filtered.map(e => {
        let statusBadge = `<span class="status-pill success">COMPLIANT</span>`;
        if (e.compliance_status === "FLAGGED_DISCREPANCY") {
          statusBadge = `<span class="status-pill danger">FLAGGED DISCREPANCY</span>`;
        } else if (e.compliance_status === "AUDIT_WARNING") {
          statusBadge = `<span class="status-pill warning">AUDIT WARNING</span>`;
        }

        return `
          <tr>
            <td><strong>${e.name}</strong><br><small>${e.entity_id}</small></td>
            <td><strong>${e.jurisdiction}</strong> (${e.tax_id})</td>
            <td><span class="badge badge-success">${e.vat_scheme}</span></td>
            <td>€${e.total_debit_eur.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
            <td>€${e.total_credit_eur.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
            <td class="${e.discrepancy_eur > 0 ? 'text-alert' : ''}"><strong>€${e.discrepancy_eur.toFixed(2)}</strong></td>
            <td>${statusBadge}</td>
          </tr>
        `;
      }).join("");
    }

    // 3. Render Live НАП E-Invoicing Stream Table
    if (data.nra_einvoice_stream && einvoicesTbody) {
      einvoicesTbody.innerHTML = data.nra_einvoice_stream.slice(0, 10).map(item => `
        <tr>
          <td><strong>${item.invoice_id}</strong></td>
          <td>${item.counterparty_name}<br><small>ЕИК: ${item.counterparty_eik}</small></td>
          <td>${item.amount_bgn.toFixed(2)} BGN</td>
          <td><span class="badge badge-success">${item.qes_algorithm}</span></td>
          <td><code>${item.cais_epp_reference}</code></td>
          <td><span class="status-pill success">${item.status}</span></td>
        </tr>
      `).join("");

      if (einvoiceStreamCount) {
        einvoiceStreamCount.innerText = `${data.nra_einvoice_stream.length} Фактури live`;
      }
    }

    // 4. Render PQC Replication Mesh Telemetry Nodes
    if (data.pqc_replication_nodes && pqcNodesContainer) {
      pqcNodesContainer.innerHTML = data.pqc_replication_nodes.map(node => `
        <div class="pqc-node-card">
          <div>
            <div class="pqc-node-title">🖥️ ${node.node_id}</div>
            <div class="pqc-node-sub">${node.region} • ${node.lattice_algorithm}</div>
          </div>
          <div style="text-align: right;">
            <div class="pqc-node-metric">${node.replication_lag_ms} ms lag</div>
            <span class="status-pill ${node.status === 'HEALTHY' ? 'success' : 'warning'}">${node.status}</span>
          </div>
        </div>
      `).join("");
    }

    // 5. Render Flagged Audit Entries Table
    if (data.flagged_entries && flaggedEntriesTbody) {
      flaggedEntriesTbody.innerHTML = data.flagged_entries.map(flag => `
        <tr>
          <td><code>${flag.entry_id}</code></td>
          <td><strong>${flag.entity_id}</strong></td>
          <td>Дб ${flag.account_debit} / Кр ${flag.account_credit}</td>
          <td>€${flag.original_debit?.toFixed(2) || '0.00'}</td>
          <td><strong class="text-alert">€${flag.discrepancy?.toFixed(2) || '0.00'}</strong></td>
          <td>${flag.issue}<br><small class="text-muted">Препоръка: ${flag.suggested_fix}</small></td>
          <td>
            <button class="btn btn-sm btn-primary" onclick="openCorrectionForEntry('${flag.entry_id}', '${flag.entity_id}', '${flag.discrepancy}')">
              🛠️ Коригирай
            </button>
          </td>
        </tr>
      `).join("");

      if (flaggedCountBadge) {
        flaggedCountBadge.innerText = `${data.flagged_entries.length} Маркирани Разхождения`;
        flaggedCountBadge.className = data.flagged_entries.length === 0 ? "badge badge-success" : "badge badge-warning";
      }
    }

    // 6. Render Corrections Ledger Table
    if (data.corrections_ledger && correctionsLedgerTbody) {
      correctionsLedgerTbody.innerHTML = data.corrections_ledger.map(c => `
        <tr>
          <td><code>${c.correction_id}</code></td>
          <td><strong>${c.entity_id}</strong></td>
          <td>${c.entry_id}</td>
          <td>€${c.corrected_amount.toFixed(2)}</td>
          <td>${c.reason}</td>
          <td><small>${new Date(c.timestamp).toLocaleTimeString()}</small></td>
          <td><code title="${c.new_audit_hash}">${c.new_audit_hash.substring(0, 12)}...</code></td>
        </tr>
      `).join("");
    }

    // 7. Render M71 Smart Auto-Reconciliation Candidates Table
    if (data.smart_reconciliation_pending && smartReconcileTbody) {
      if (data.smart_reconciliation_pending.length === 0) {
        smartReconcileTbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; color: #10b981; padding: 2rem;">
              ✅ Всички AI препоръки за засичане на фактури са потвърдени! Няма чакащи съвпадения.
            </td>
          </tr>
        `;
      } else {
        smartReconcileTbody.innerHTML = data.smart_reconciliation_pending.map(m => {
          const confPct = m.overall_confidence_pct || (m.overall_confidence * 100).toFixed(1);
          let badgeClass = "badge badge-success";
          if (confPct < 85) badgeClass = "badge badge-warning";
          if (confPct < 65) badgeClass = "badge badge-danger";

          const je = m.suggested_journal_entry || {};
          const jeStr = `Дб ${je.debit_account || '503'} / Кр ${je.credit_account || '411'} (${(je.amount_bgn || m.invoice_amount).toFixed(2)} лв)`;

          return `
            <tr>
              <td>
                <strong>#${m.invoice_number}</strong><br>
                <small>${m.invoice_counterparty}</small><br>
                <span class="text-muted">${m.invoice_amount.toFixed(2)} ${m.currency}</span>
              </td>
              <td>
                <strong>${m.bank_tx_id}</strong><br>
                <small>${m.bank_tx_narrative}</small><br>
                <span class="text-muted">${m.bank_tx_amount.toFixed(2)} BGN</span>
              </td>
              <td>
                <span class="${badgeClass}">🤖 ${confPct}%</span><br>
                <small class="text-muted">${m.confidence_tier}</small>
              </td>
              <td>
                <strong>${m.amount_difference.toFixed(2)} лв</strong><br>
                <small class="text-muted">${m.amount_difference === 0 ? 'Точна сума' : 'Fuzzy толеранс'}</small>
              </td>
              <td>
                <small>${m.match_notes}</small>
              </td>
              <td>
                <code>${jeStr}</code>
              </td>
              <td>
                <div style="display: flex; gap: 0.5rem;">
                  <button class="btn btn-sm btn-primary" onclick="confirmSmartMatch('${m.match_id}')">
                    ✅ Потвърди
                  </button>
                  <button class="btn btn-sm btn-secondary" onclick="rejectSmartMatch('${m.match_id}')">
                    ✕ Отхвърли
                  </button>
                </div>
              </td>
            </tr>
          `;
        }).join("");
      }

      if (smartMatchCountBadge) {
        const cnt = data.smart_reconciliation_pending.length;
        smartMatchCountBadge.innerText = `AI Засичания: ${cnt} Чакат Потвърждение`;
        smartMatchCountBadge.className = cnt === 0 ? "badge badge-success" : "badge badge-warning";
      }
    }
  };

  // 1-Click Confirmation & Rejection Handlers for M71 Smart Reconciliation
  window.confirmSmartMatch = async (matchId) => {
    console.log(`🤖 1-Click confirming M71 match: ${matchId}`);
    try {
      const resp = await fetch("/api/v1/reconciliation/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ match_id: matchId, confirmed_by: "accountant_ui_user" }),
      });
      if (resp.ok) {
        const res = await resp.json();
        console.log("✅ Match confirmed:", res);
        fetchTelemetryREST();
      } else {
        alert("Грешка при потвърждаване на съвпадението.");
      }
    } catch (e) {
      alert(`Грешка при мрежова заявка: ${e}`);
    }
  };

  window.rejectSmartMatch = async (matchId) => {
    console.log(`🤖 Rejecting M71 match: ${matchId}`);
    try {
      const resp = await fetch("/api/v1/reconciliation/reject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ match_id: matchId }),
      });
      if (resp.ok) {
        fetchTelemetryREST();
      }
    } catch (e) {
      console.warn("Reject request error:", e);
    }
  };

  // --- Interactive Form & Actions ---

  // Entity Tabs Filter
  entityTabsContainer?.addEventListener("click", (e) => {
    const target = e.target;
    if (target.classList.contains("tab-btn")) {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      target.classList.add("active");
      activeEntityFilter = target.getAttribute("data-entity");
      if (telemetryData) renderDashboard(telemetryData);
    }
  });

  // Modal Handlers
  const openModal = () => correctionModal?.classList.remove("hidden");
  const closeModal = () => correctionModal?.classList.add("hidden");

  window.openCorrectionForEntry = (entryId, entityId, amount) => {
    document.getElementById("modal-entry-id").value = entryId;
    document.getElementById("modal-entity-id").value = entityId;
    document.getElementById("modal-corrected-amount").value = amount || "150.00";
    openModal();
  };

  btnOpenCorrectionModal?.addEventListener("click", openModal);
  btnCloseModal?.addEventListener("click", closeModal);
  btnCancelModal?.addEventListener("click", closeModal);

  // Submit Audit Correction Form
  correctionForm?.addEventListener("submit", async (e) => {
    e.preventDefault();

    const correctionData = {
      action: "correct_entry",
      entry_id: document.getElementById("modal-entry-id").value,
      entity_id: document.getElementById("modal-entity-id").value,
      account_debit: document.getElementById("modal-acc-debit").value,
      account_credit: document.getElementById("modal-acc-credit").value,
      corrected_amount: parseFloat(document.getElementById("modal-corrected-amount").value),
      reason: document.getElementById("modal-reason").value,
    };

    if (wsSocket && wsSocket.readyState === WebSocket.OPEN) {
      wsSocket.send(JSON.stringify(correctionData));
      console.log("⚡ Sent audit correction payload over WebSockets stream!");
    } else {
      try {
        const resp = await fetch("/api/compliance/correct", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(correctionData),
        });
        if (resp.ok) {
          const res = await resp.json();
          console.log("✅ Audit correction applied via REST:", res);
          fetchTelemetryREST();
        }
      } catch (err) {
        alert(`Грешка при изпращане на корекция: ${err}`);
      }
    }

    closeModal();
  });

  // Action Button: Simulate NRA E-Invoice
  btnTriggerEinvoice?.addEventListener("click", async () => {
    const payload = {
      action: "submit_einvoice",
      counterparty_name: "Булкомплект АД",
      counterparty_eik: "991029381",
      amount_bgn: 2500.00,
    };

    if (wsSocket && wsSocket.readyState === WebSocket.OPEN) {
      wsSocket.send(JSON.stringify(payload));
    } else {
      await fetch("/api/compliance/einvoice/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      fetchTelemetryREST();
    }
  });

  // Action Button: Sync PQC Mesh Node
  btnSyncMesh?.addEventListener("click", async () => {
    const payload = {
      action: "sync_pqc_node",
      node_id: "hetzner-fsn1-dc14",
    };

    if (wsSocket && wsSocket.readyState === WebSocket.OPEN) {
      wsSocket.send(JSON.stringify(payload));
    } else {
      await fetch("/api/compliance/mesh/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      fetchTelemetryREST();
    }
  });

  // Initialize WebSockets connection
  connectWebSocket();
});
