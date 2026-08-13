# Phase 22 Strategic Roadmap: Production Deployment, User Documentation & Multi-Tenant SaaS Readiness

## Vision & Objective
Phase 22 transitions the FinansProtect platform from feature-complete development into **production-grade deployment** with comprehensive user documentation and commercial billing infrastructure. This phase transforms the platform from an engineering achievement into a deployable, documented, and monetizable product.

---

## Strategic Milestones

### Milestone M73: Production Kubernetes Deployment & Helm Charts (`m73_k8s_helm_deployment`)
- **Objective**: Package the entire FinansProtect stack as a production-ready Helm chart for K3s/K8s deployment across on-premise Mac Mini clusters, Hetzner Cloud, and AWS EKS.
- **Scope**:
  - Helm chart (`deploy/helm/finansprotect/`) with all microservices defined as Kubernetes Deployments/StatefulSets.
  - K3s manifests for existing Mac Mini HA cluster (`macmini-primary` 100.83.83.8 / `macmini-secondary` 100.70.181.127).
  - Namespace isolation: `finansprotect-prod`, `finansprotect-staging`, `finansprotect-dev`.
  - Automated TLS provisioning via cert-manager + Let's Encrypt.
  - Horizontal Pod Autoscaler (HPA) for OCR, AI inference, and API gateway workloads.
  - PersistentVolumeClaim templates for QEMU disk images (`windows11_portable.qcow2`), audit logs, and cold storage archives.
  - ConfigMap and Secret integration with existing Infisical Vault (M69).
  - Ingress controller configuration (Traefik / Nginx) with rate limiting and WAF rules.
  - Health check probes (liveness, readiness, startup) for all services.
  - Prometheus ServiceMonitor and Grafana dashboard provisioning.
  - Automated database migration jobs (InitContainer pattern).
  - CI/CD pipeline extension: GitHub Actions → Build → Push to GHCR → Deploy via Helm.
- **Dependencies**: M10, M18, M34, M63, M69
- **Target Deliverables**: `deploy/helm/`, `deploy/k3s/`, `.github/workflows/deploy.yml`
- **Status**: In Progress

### Milestone M74: Comprehensive User Manual & Administrator Guide (`m74_user_documentation`)
- **Objective**: Create bilingual (BG/EN) end-user and administrator documentation enabling self-service onboarding, configuration, and daily operation of the FinansProtect platform.
- **Scope**:
  - MkDocs Material documentation site (`docs/site/`).
  - Quick Start Guide (Ръководство за бърз старт / Quick Start — 15-minute setup).
  - Administrator Guide: QEMU VM setup, Delta Pro configuration, SQL Server connection, Infisical secrets, HA cluster setup.
  - User Manual: Dashboard usage, invoice upload, OCR processing, reconciliation workflows, ГФО generation.
  - API Developer Guide with OpenAPI reference, authentication, rate limits, and Postman collection.
  - Troubleshooting Guide: Common errors, log locations, health check endpoints.
  - Bulgarian (BG) and English (EN) parallel documentation.
  - Embedded screenshots and workflow diagrams.
- **Dependencies**: M12, M70
- **Target Deliverables**: `docs/site/`, `docs/mkdocs.yml`, `docs/postman_collection.json`
- **Status**: In Progress

### Milestone M75: Multi-Tenant SaaS Billing & Subscription Management (`m75_saas_billing`)
- **Objective**: Enable commercial multi-tenant deployment with automated billing, usage metering, and tenant lifecycle management.
- **Scope**:
  - Stripe payment integration for subscription tiers (Free / Professional / Enterprise).
  - Tenant provisioning REST API (`POST /api/v1/tenants`, `DELETE /api/v1/tenants/{id}`).
  - Usage-based metering engine (processed statements, API calls, AI inference queries).
  - Tenant-isolated database schemas (shared PostgreSQL, per-tenant schema).
  - Admin panel for tenant management, billing history, and usage analytics.
  - GDPR Art. 17 right-to-erasure implementation across all data stores.
  - Webhook-driven billing event processing (invoice.paid, subscription.cancelled).
- **Dependencies**: M15, M69, M73
- **Target Deliverables**: `src/billing/`, `tests/billing/`, `src/dashboard/web_ui/admin.html`
- **Status**: Completed


---

## Verification Criteria
- M73: `helm install` deploys full stack on K3s cluster; all health checks pass; Prometheus metrics available.
- M74: MkDocs site builds and serves locally; all pages render correctly in BG and EN.
- M75: Stripe test-mode subscription lifecycle works end-to-end; tenant CRUD operations pass integration tests.
