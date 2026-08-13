import os

docs_dir = "/Users/diokarabaz/orca/workspaces/2026-08-05/работно-пространство/docs/site"
os.makedirs(docs_dir, exist_ok=True)

files = {
    "index.md": "# FinansProtect Platform Documentation\n\nWelcome to the official documentation for the FinansProtect platform.\n\nSelect a language from the navigation menu to begin:\n- Български\n- English\n",
    "bg/quick-start.md": "# Бърз старт\n\nТова ръководство ще ви помогне да инсталирате и стартирате FinansProtect за 15 минути.\n\n## Изисквания\n- Python 3.11+\n- Docker & Docker Compose\n- QEMU\n\n## Инсталация\n```bash\ngit clone https://github.com/finansprotect/platform.git\ncd platform\ndocker-compose up -d\n```\n",
    "bg/admin/installation.md": "# Инсталация\n\nПодробно ръководство за инсталация на различни среди.\n\n## Docker\nЗа стандартна инсталация използвайте `docker-compose`.\n",
    "bg/admin/qemu-setup.md": "# QEMU Настройка\n\nНастройка на Windows 11 QEMU VM за Delta Pro.\n\nИзползвайте предоставения `autounattend.xml` за автоматична инсталация.\n",
    "bg/admin/configuration.md": "# Конфигурация\n\nОсновни настройки се намират в `config.yaml`.\n\n```yaml\ndatabase:\n  host: localhost\n  port: 5432\n```\n",
    "bg/admin/ha-cluster.md": "# HA Клъстер\n\nНастройка на High Availability (HA) клъстер между няколко Mac Mini нода.\n",
    "bg/admin/backup-dr.md": "# Резервни копия и DR\n\nСтратегии за бекъп и възстановяване при бедствия (Disaster Recovery).\n",
    "bg/admin/monitoring.md": "# Мониторинг\n\nНастройка на Prometheus, Grafana и аларми.\n",
    "bg/admin/security.md": "# Сигурност\n\nУправление на достъпа (RBAC), JWT токени, HSM/PQC подписване.\n",
    "bg/user/dashboard.md": "# Табло\n\nИзползване на таблото на FinansProtect (достъпно на порт 8095).\n",
    "bg/user/ocr-processing.md": "# OCR Обработка\n\nКачване на банкови извлечения и обработка чрез OCR.\n",
    "bg/user/reconciliation.md": "# Съвпадение на фактури\n\nАвтоматично съвпадение и равнение (M71).\n",
    "bg/user/gfo-reports.md": "# ГФО Отчети\n\nГенериране на Годишен финансов отчет (ГФО).\n",
    "bg/user/tax-compliance.md": "# Данъчно съответствие\n\nДДС декларации, ЗКПО, данък дивидент, НАП електронни фактури.\n",
    "bg/user/anaf-efactura.md": "# Румъния ANAF e-Factura (M78)\n\nИнтеграция с румънската данъчна портална система ANAF за e-Factura. Генериране на UBL 2.1 RO-CIUS XML, валидация на CUI/CIF, OAuth 2.0 SPV автентикация, QES/XMLDSig дигитален подпис и проверка в ANAF VAT регистър.\n",
    "bg/user/ksef-gateway.md": "# Полша KSeF Gateway (M79)\n\nИнтеграция с полската държавна портална система KSeF (Krajowy System e-Faktur) към Министерството на финансите на Полша. Генериране на FA(2)/FA(3) XML фактури, NIP валидация по Modulo 11, Session Token автентикация, XAdES дигитален подпис, сваляне на UPO разписки и реално време проверка на компании през GUS BIR1.1 API.\n",
    "bg/user/banking.md": "# Банкиране\n\nОтворено банкиране, SEPA плащания и мониторинг.\n",

    "bg/user/ai-features.md": "# AI Функции\n\nAI детекция на измами, гласов асистент и предвиждания.\n",
    "bg/api/overview.md": "# API Общ преглед\n\nАрхитектура, автентикация и лимити на REST API.\n",
    "bg/api/endpoints.md": "# Крайни точки\n\nСписък с всички API endpoints.\n",
    "bg/api/webhooks.md": "# Webhooks\n\nСъбития и структури на webhook заявките.\n",
    "bg/api/errors.md": "# Грешки\n\nКодове за грешки и тяхното значение.\n",
    "bg/troubleshooting.md": "# Отстраняване на проблеми\n\nЧесто срещани грешки и техните решения.\n",

    "en/quick-start.md": "# Quick Start\n\n15-minute setup guide for FinansProtect.\n\n## Prerequisites\n- Python 3.11+\n- Docker\n- QEMU\n",
    "en/admin/installation.md": "# Installation\n\nFull installation guide for Docker, bare metal, and K8s.\n",
    "en/admin/qemu-setup.md": "# QEMU Setup\n\nWindows 11 QEMU VM setup and Delta Pro installation.\n",
    "en/admin/configuration.md": "# Configuration\n\nReference for `config.yaml`, env vars, and secrets.\n",
    "en/admin/ha-cluster.md": "# HA Cluster\n\nHigh availability cluster setup across Mac Mini nodes.\n",
    "en/admin/backup-dr.md": "# Backup & DR\n\nBackup, disaster recovery, and cold storage config.\n",
    "en/admin/monitoring.md": "# Monitoring\n\nPrometheus, Grafana, and alerting setup.\n",
    "en/admin/security.md": "# Security\n\nRBAC, JWT, HSM/PQC signing, and network security.\n",
    "en/user/dashboard.md": "# Dashboard\n\nUsing the FinansProtect Dashboard (port 8095).\n",
    "en/user/ocr-processing.md": "# OCR Processing\n\nBank statement upload and OCR extraction.\n",
    "en/user/reconciliation.md": "# Reconciliation\n\nInvoice matching and auto-reconciliation.\n",
    "en/user/gfo-reports.md": "# GFO Reports\n\nAnnual Financial Statement (ГФО) generation.\n",
    "en/user/tax-compliance.md": "# Tax Compliance\n\nVAT returns, CITA, dividend tax, NRA e-invoicing.\n",
    "en/user/anaf-efactura.md": "# Romania ANAF e-Factura (M78)\n\nIntegration with Romanian ANAF e-Factura portal system. UBL 2.1 RO-CIUS XML generation, CUI/CIF check digit validation, OAuth 2.0 SPV authentication, QES/XMLDSig signing, and ANAF VAT Registry lookup.\n",
    "en/user/ksef-gateway.md": "# Poland KSeF Gateway (M79)\n\nIntegration with Polish Ministry of Finance National e-Invoice System KSeF (Krajowy System e-Faktur). FA(2)/FA(3) XML invoice generation, Modulo 11 NIP validation, Session Token authentication, XAdES digital signature wrapper, UPO receipt downloading, and real-time company verification via GUS BIR1.1 API.\n",
    "en/user/banking.md": "# Banking\n\nOpen banking, SEPA payments, bank feed monitoring.\n",

    "en/user/ai-features.md": "# AI Features\n\nAI fraud detection, predictive analytics.\n",
    "en/api/overview.md": "# API Overview\n\nArchitecture, authentication, rate limits.\n",
    "en/api/endpoints.md": "# Endpoints\n\nFull endpoint reference.\n",
    "en/api/webhooks.md": "# Webhooks\n\nWebhook events and payload schemas.\n",
    "en/api/errors.md": "# Errors\n\nError codes and troubleshooting.\n",
    "en/troubleshooting.md": "# Troubleshooting\n\nCommon errors and solutions.\n",
}

for filepath, content in files.items():
    full_path = os.path.join(docs_dir, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
