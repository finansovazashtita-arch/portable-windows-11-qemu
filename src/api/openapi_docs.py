#!/usr/bin/env python3
"""
FinansProtect Comprehensive API Documentation, OpenAPI 3.1 Specification,
Schema Validation Middleware, and API Versioning Strategy (M70).

Provides OpenAPI 3.1 YAML/JSON generation, interactive Swagger UI dashboard integration (/api/docs),
request/response JSON schema validation middleware, and v1/v2 API version routing.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import yaml

logger = logging.getLogger("openapi_docs")

OPENAPI_SPEC_VERSION = "3.1.0"
API_TITLE = "FinansProtect Enterprise Compliance & Audit REST API"
API_VERSION = "2.0.0"
API_DESCRIPTION = """
# FinansProtect Enterprise API

The FinansProtect API delivers real-time Bulgarian & EU multi-entity tax compliance monitoring, 
NRA (НАП) E-Invoice SAF-T stream processing, post-quantum cryptographic mesh replication, 
edge-AI mobile receipt scanning, and automated double-entry accounting reconciliation.

## Features
- **API Versioning**: Supports path versioning (`/api/v1/...`, `/api/v2/...`) and header-based versioning (`X-API-Version`).
- **Schema Validation**: Built-in OpenAPI 3.1 request and response payload validation middleware.
- **Interactive Documentation**: Embedded Swagger UI accessible via `/api/docs`.
- **Security**: OAuth2 Bearer Token and API Key authentication schemes.
"""

OPENAPI_SPEC: Dict[str, Any] = {
    "openapi": OPENAPI_SPEC_VERSION,
    "info": {
        "title": API_TITLE,
        "summary": "Real-time EU Multi-Entity Compliance & Accounting API",
        "description": API_DESCRIPTION,
        "version": API_VERSION,
        "termsOfService": "https://finansprotect.bg/terms",
        "contact": {
            "name": "FinansProtect Enterprise Support",
            "email": "support@finansprotect.bg",
            "url": "https://finansprotect.bg/support"
        },
        "license": {
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        }
    },
    "servers": [
        {"url": "http://127.0.0.1:8095", "description": "Local Dashboard Server"},
        {"url": "http://localhost:8095", "description": "Local Development Server"},
        {"url": "https://api.finansprotect.bg", "description": "Production Cluster Gateway"}
    ],
    "tags": [
        {"name": "Telemetry", "description": "System health, entity metrics, and PQC mesh telemetry"},
        {"name": "Compliance", "description": "Real-time compliance summary, discrepancy corrections & NRA E-Invoicing"},
        {"name": "Smart Reconciliation", "description": "M71 AI-powered narrative vector embedding matching, fuzzy amount auto-reconciliation, and 1-click accountant confirmation"},
        {"name": "Mobile Suite", "description": "Edge-AI fiscal receipt processing, WASM OCR status, and offline queue sync"},
        {"name": "SaaS Billing", "description": "M75 Stripe subscription management, multi-tenant provisioning, usage metering, and GDPR Art. 17 data erasure"},
        {"name": "Documentation", "description": "OpenAPI specifications & interactive UI endpoints"}
    ],
    "paths": {

        "/api/docs": {
            "get": {
                "tags": ["Documentation"],
                "summary": "Interactive Swagger UI Dashboard",
                "description": "Renders interactive HTML Swagger UI for inspecting and testing API endpoints.",
                "operationId": "getSwaggerUI",
                "responses": {
                    "200": {
                        "description": "HTML page containing Swagger UI viewer",
                        "content": {"text/html": {}}
                    }
                }
            }
        },
        "/api/openapi.json": {
            "get": {
                "tags": ["Documentation"],
                "summary": "OpenAPI 3.1 Specification (JSON)",
                "description": "Returns full OpenAPI 3.1 spec in JSON format.",
                "operationId": "getOpenAPISpecJSON",
                "responses": {
                    "200": {
                        "description": "OpenAPI 3.1 JSON Specification",
                        "content": {"application/json": {}}
                    }
                }
            }
        },
        "/api/openapi.yaml": {
            "get": {
                "tags": ["Documentation"],
                "summary": "OpenAPI 3.1 Specification (YAML)",
                "description": "Returns full OpenAPI 3.1 spec in YAML format.",
                "operationId": "getOpenAPISpecYAML",
                "responses": {
                    "200": {
                        "description": "OpenAPI 3.1 YAML Specification",
                        "content": {"text/yaml": {}}
                    }
                }
            }
        },
        "/api/v1/telemetry": {
            "get": {
                "tags": ["Telemetry"],
                "summary": "System & Compliance Telemetry (v1)",
                "description": "Returns current overall compliance score, grand total balances, audit SHA-256 head, and service connectivity.",
                "operationId": "getTelemetryV1",
                "responses": {
                    "200": {
                        "description": "Successful telemetry response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/TelemetryResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/v2/telemetry": {
            "get": {
                "tags": ["Telemetry"],
                "summary": "System & Compliance Telemetry (v2)",
                "description": "Enhanced v2 telemetry endpoint with API version metadata, detailed latency metrics, and PQC mesh status.",
                "operationId": "getTelemetryV2",
                "responses": {
                    "200": {
                        "description": "Enhanced v2 telemetry response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/TelemetryResponseV2"}
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/compliance/summary": {
            "get": {
                "tags": ["Compliance"],
                "summary": "Multi-Entity Compliance Summary",
                "description": "Retrieves comprehensive multi-entity compliance status, active NRA E-Invoice streams, and PQC nodes.",
                "operationId": "getComplianceSummary",
                "responses": {
                    "200": {
                        "description": "Full compliance payload",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ComplianceSummaryResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/compliance/telemetry": {
            "get": {
                "tags": ["Compliance"],
                "summary": "Compliance Engine Telemetry",
                "description": "Alias endpoint for compliance engine raw telemetry payload.",
                "operationId": "getComplianceTelemetry",
                "responses": {
                    "200": {
                        "description": "Compliance raw telemetry",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ComplianceSummaryResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/mobile/status": {
            "get": {
                "tags": ["Mobile Suite"],
                "summary": "Edge-AI Mobile Suite Status",
                "description": "Checks edge WASM OCR engine health and offline receipt queue counts.",
                "operationId": "getMobileStatus",
                "responses": {
                    "200": {
                        "description": "Mobile engine status response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/MobileStatusResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/mobile/scan": {
            "post": {
                "tags": ["Mobile Suite"],
                "summary": "Process Edge Fiscal Receipt Scan",
                "description": "Processes raw fiscal receipt OCR text and NRA QR code string, returning double-entry accounting journal entries.",
                "operationId": "scanMobileReceipt",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/MobileScanRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Receipt processed successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/MobileScanResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid correction payload",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/reconciliation/pending-matches": {
            "get": {
                "tags": ["Smart Reconciliation"],
                "summary": "Get Pending AI Reconciled Pairs",
                "description": "Returns AI-suggested match pairs (Invoice <-> Bank Row) awaiting 1-click accountant confirmation.",
                "operationId": "getPendingReconciliationMatches",
                "responses": {
                    "200": {
                        "description": "List of pending smart reconciliation match candidates",
                        "content": {"application/json": {}}
                    }
                }
            }
        },
        "/api/v1/reconciliation/smart-match": {
            "post": {
                "tags": ["Smart Reconciliation"],
                "summary": "Batch AI Invoice-to-Bank Auto-Matching",
                "description": "Executes vector embedding narrative matching & fuzzy amount matching on invoice & bank transaction lists.",
                "operationId": "executeSmartMatchBatch",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {}
                    }
                },
                "responses": {
                    "200": {
                        "description": "AI smart reconciliation candidates generated",
                        "content": {"application/json": {}}
                    }
                }
            }
        },
        "/api/v1/reconciliation/confirm": {
            "post": {
                "tags": ["Smart Reconciliation"],
                "summary": "1-Click Accountant Confirmation",
                "description": "Confirms an AI-recommended match candidate, posts double-entry journal entry, and updates SHA-256 audit hash chain.",
                "operationId": "confirmReconciliationMatch",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {}
                    }
                },
                "responses": {
                    "200": {
                        "description": "Match confirmed and double-entry posted",
                        "content": {"application/json": {}}
                    }
                }
            }
        },
        "/api/v1/reconciliation/reject": {
            "post": {
                "tags": ["Smart Reconciliation"],
                "summary": "Reject AI Reconciled Candidate",
                "description": "Rejects an AI-recommended match pair candidate from the auto-suggest queue.",
                "operationId": "rejectReconciliationMatch",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {}
                    }
                },
                "responses": {
                    "200": {
                        "description": "Match candidate rejected",
                        "content": {"application/json": {}}
                    }
                }
            }
        },
        "/api/v1/mobile/sync": {
            "post": {
                "tags": ["Mobile Suite"],
                "summary": "Synchronize Offline Receipts Queue",
                "description": "Flushes enqueued offline fiscal receipts to the server audit ledger.",
                "operationId": "syncMobileOfflineQueue",
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Offline receipts synchronized successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/MobileSyncResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/compliance/correct": {
            "post": {
                "tags": ["Compliance"],
                "summary": "Submit Interactive Audit Correction",
                "description": "Resolves compliance audit discrepancies with CPA auditor digital signature.",
                "operationId": "submitCorrection",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/CorrectionRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Correction accepted and ledger updated",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CorrectionResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid correction payload or missing fields",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/compliance/einvoice/submit": {
            "post": {
                "tags": ["Compliance"],
                "summary": "Submit NRA SAF-T E-Invoice",
                "description": "Submits structured E-Invoice payload for NRA validation and real-time ledger recording.",
                "operationId": "submitEInvoice",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/EInvoiceRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "E-Invoice validated and recorded",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/EInvoiceResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "E-Invoice schema validation failure",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/compliance/mesh/sync": {
            "post": {
                "tags": ["Compliance", "Telemetry"],
                "summary": "Trigger Post-Quantum Mesh Node Sync",
                "description": "Initiates PQC replication mesh state synchronization across multi-datacenter nodes.",
                "operationId": "syncMeshNode",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/MeshSyncRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "PQC Node sync initiated successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/MeshSyncResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Node synchronization error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/tenants": {
            "get": {
                "tags": ["SaaS Billing"],
                "summary": "List Tenants",
                "description": "Retrieves paginated list of multi-tenant accounts with tier and status filtering.",
                "parameters": [
                    {"name": "tier", "in": "query", "schema": {"type": "string", "enum": ["FREE", "PROFESSIONAL", "ENTERPRISE"]}},
                    {"name": "status", "in": "query", "schema": {"type": "string"}},
                    {"name": "search", "in": "query", "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50}},
                    {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}}
                ],
                "responses": {
                    "200": {"description": "List of tenant records"}
                }
            },
            "post": {
                "tags": ["SaaS Billing"],
                "summary": "Provision New Tenant",
                "description": "Provisions isolated database schema, Stripe customer account, and default quota meters for a new tenant.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["company_name", "eik", "contact_email"],
                                "properties": {
                                    "company_name": {"type": "string", "example": "Булгартрансгаз ЕАД"},
                                    "eik": {"type": "string", "example": "117541341"},
                                    "contact_email": {"type": "string", "example": "billing@bulgartransgaz.bg"},
                                    "tier": {"type": "string", "enum": ["FREE", "PROFESSIONAL", "ENTERPRISE"], "default": "FREE"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "201": {"description": "Tenant successfully provisioned"},
                    "400": {"description": "Invalid UIC/EIK or missing parameters"}
                }
            }
        },
        "/api/v1/tenants/{tenant_id}": {
            "get": {
                "tags": ["SaaS Billing"],
                "summary": "Get Tenant Details & Quota Status",
                "description": "Returns tenant metadata, schema info, and current quota consumption.",
                "parameters": [
                    {"name": "tenant_id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {
                    "200": {"description": "Tenant details and usage snapshot"},
                    "404": {"description": "Tenant not found"}
                }
            },
            "put": {
                "tags": ["SaaS Billing"],
                "summary": "Update Tenant Metadata",
                "parameters": [
                    {"name": "tenant_id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {"200": {"description": "Tenant updated"}}
            },
            "delete": {
                "tags": ["SaaS Billing"],
                "summary": "Delete Tenant Account",
                "parameters": [
                    {"name": "tenant_id", "in": "path", "required": True, "schema": {"type": "string"}},
                    {"name": "purge", "in": "query", "schema": {"type": "boolean", "default": True}}
                ],
                "responses": {"200": {"description": "Tenant deleted and purged"}}
            }
        },
        "/api/v1/tenants/{tenant_id}/gdpr-erasure": {
            "post": {
                "tags": ["SaaS Billing"],
                "summary": "GDPR Article 17 Right-to-Erasure",
                "description": "Executes complete data wipe, schema drop, audit log anonymization, and generates signed Erasure Certificate.",
                "parameters": [
                    {"name": "tenant_id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {
                    "200": {"description": "Erasure certificate generated and data purged"}
                }
            }
        },
        "/api/v1/billing/checkout-session": {
            "post": {
                "tags": ["SaaS Billing"],
                "summary": "Create Stripe Checkout Session",
                "responses": {"200": {"description": "Checkout session created"}}
            }
        },
        "/api/v1/billing/portal-session": {
            "post": {
                "tags": ["SaaS Billing"],
                "summary": "Create Stripe Customer Portal Session",
                "responses": {"200": {"description": "Portal session URL generated"}}
            }
        },
        "/api/v1/billing/webhooks/stripe": {
            "post": {
                "tags": ["SaaS Billing"],
                "summary": "Stripe Webhook Handler",
                "description": "Processes subscription created/updated/deleted and invoice.paid events with signature verification and idempotency protection.",
                "responses": {"200": {"description": "Webhook processed"}}
            }
        }
    },
    "components": {

        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "OAuth2 Bearer JWT authorization token."
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "FinansProtect Enterprise API key."
            }
        },
        "schemas": {
            "TelemetryResponse": {
                "type": "object",
                "required": ["status", "overall_compliance_score", "grand_total_debits", "grand_total_credits", "discrepancy", "audit_sha256"],
                "properties": {
                    "status": {"type": "string", "example": "ONLINE"},
                    "overall_compliance_score": {"type": "number", "example": 99.4},
                    "grand_total_debits": {"type": "string", "example": "125,400.00"},
                    "grand_total_credits": {"type": "string", "example": "125,400.00"},
                    "discrepancy": {"type": "string", "example": "0.00 EUR"},
                    "audit_sha256": {"type": "string", "example": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
                    "qemu_vm_status": {"type": "string", "example": "CONNECTED_127.0.0.1:5901"},
                    "infisical_vault": {"type": "string", "example": "CONNECTED"},
                    "n8n_automation": {"type": "string", "example": "ACTIVE"},
                    "entities_count": {"type": "integer", "example": 3},
                    "nra_einvoice_count": {"type": "integer", "example": 12},
                    "pqc_nodes_count": {"type": "integer", "example": 4}
                }
            },
            "TelemetryResponseV2": {
                "type": "object",
                "required": ["api_version", "status", "overall_compliance_score", "timestamp"],
                "properties": {
                    "api_version": {"type": "string", "example": "2.0.0"},
                    "status": {"type": "string", "example": "ONLINE"},
                    "overall_compliance_score": {"type": "number", "example": 99.4},
                    "timestamp": {"type": "number", "example": 1770900000.0},
                    "summary": {"type": "object"},
                    "pqc_nodes_online": {"type": "integer", "example": 4}
                }
            },
            "ComplianceSummaryResponse": {
                "type": "object",
                "required": ["system_status", "overall_compliance_score", "entities", "summary"],
                "properties": {
                    "system_status": {"type": "string", "example": "ONLINE"},
                    "overall_compliance_score": {"type": "number", "example": 99.4},
                    "entities": {"type": "array", "items": {"type": "object"}},
                    "summary": {"type": "object"},
                    "nra_einvoice_stream": {"type": "array", "items": {"type": "object"}},
                    "pqc_replication_nodes": {"type": "array", "items": {"type": "object"}}
                }
            },
            "MobileStatusResponse": {
                "type": "object",
                "required": ["status", "edge_ocr_wasm_engine", "queued_scans_count", "synced_scans_count"],
                "properties": {
                    "status": {"type": "string", "example": "ONLINE"},
                    "edge_ocr_wasm_engine": {"type": "string", "example": "ACTIVE"},
                    "queued_scans_count": {"type": "integer", "example": 0},
                    "synced_scans_count": {"type": "integer", "example": 15}
                }
            },
            "MobileScanRequest": {
                "type": "object",
                "required": ["ocr_text"],
                "properties": {
                    "ocr_text": {"type": "string", "example": "ФИСКАЛЕН БОН\\nЕТАП 2000 ЕООД\\nЕИК 114077876\\nОБЩО: 45.80"},
                    "nra_qr_string": {"type": "string", "example": "114077876*2026-01-15*14:30*45.80"},
                    "is_offline": {"type": "boolean", "example": False},
                    "accountable_person": {"type": "string", "example": "ИВАН ИВАНОВ"}
                }
            },
            "MobileScanResponse": {
                "type": "object",
                "required": ["success"],
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "offline": {"type": "boolean", "example": False},
                    "receipt": {"type": "object"},
                    "journal_entry": {"type": "object"}
                }
            },
            "MobileSyncResponse": {
                "type": "object",
                "required": ["success", "sync_result"],
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "sync_result": {"type": "object"}
                }
            },
            "CorrectionRequest": {
                "type": "object",
                "required": ["discrepancy_id", "resolution"],
                "properties": {
                    "discrepancy_id": {"type": "string", "example": "DISC_BG_001"},
                    "resolution": {"type": "string", "example": "RESOLVED_MANUAL_AUDIT"},
                    "auditor": {"type": "string", "example": "Senior CPA Auditor"}
                }
            },
            "CorrectionResponse": {
                "type": "object",
                "required": ["success", "discrepancy_id"],
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "discrepancy_id": {"type": "string", "example": "DISC_BG_001"},
                    "new_status": {"type": "string", "example": "RESOLVED"}
                }
            },
            "EInvoiceRequest": {
                "type": "object",
                "required": ["invoice_number", "supplier_eik", "buyer_eik", "total_amount_eur"],
                "properties": {
                    "invoice_number": {"type": "string", "example": "1000000045"},
                    "supplier_eik": {"type": "string", "example": "114077876"},
                    "buyer_eik": {"type": "string", "example": "201234567"},
                    "total_amount_eur": {"type": "number", "example": 1200.00}
                }
            },
            "EInvoiceResponse": {
                "type": "object",
                "required": ["success"],
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "nra_hash": {"type": "string", "example": "a1b2c3d4e5f6..."},
                    "status": {"type": "string", "example": "NRA_ACKNOWLEDGED"}
                }
            },
            "MeshSyncRequest": {
                "type": "object",
                "required": ["node_id"],
                "properties": {
                    "node_id": {"type": "string", "example": "hetzner-fsn1-dc14"}
                }
            },
            "MeshSyncResponse": {
                "type": "object",
                "required": ["success", "node_id"],
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "node_id": {"type": "string", "example": "hetzner-fsn1-dc14"},
                    "pqc_status": {"type": "string", "example": "IN_SYNC"}
                }
            },
            "ErrorResponse": {
                "type": "object",
                "required": ["error", "message"],
                "properties": {
                    "error": {"type": "string", "example": "SCHEMA_VALIDATION_ERROR"},
                    "message": {"type": "string", "example": "Missing required property 'discrepancy_id'"},
                    "details": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    }
}


def get_openapi_dict() -> Dict[str, Any]:
    """Returns Python dictionary representation of OpenAPI 3.1 specification."""
    return OPENAPI_SPEC


def get_openapi_yaml() -> str:
    """Returns YAML formatted OpenAPI 3.1 specification string."""
    return yaml.dump(OPENAPI_SPEC, sort_keys=False, allow_unicode=True)


def get_openapi_json() -> str:
    """Returns formatted JSON string of OpenAPI 3.1 specification."""
    return json.dumps(OPENAPI_SPEC, indent=2, ensure_ascii=False)


def get_swagger_ui_html(
    title: str = "FinansProtect API Documentation",
    openapi_url: str = "/api/openapi.json"
) -> str:
    """
    Renders interactive Swagger UI HTML page.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
  <link rel="icon" type="image/png" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/favicon-32x32.png" />
  <style>
    html {{
      box-sizing: border-box;
      overflow: -moz-scrollbars-vertical;
      overflow-y: scroll;
    }}
    *, *:before, *:after {{
      box-sizing: inherit;
    }}
    body {{
      margin: 0;
      background: #0f172a;
      color: #f8fafc;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    .swagger-ui .topbar {{
      background-color: #1e293b;
      padding: 10px 0;
      border-bottom: 2px solid #3b82f6;
    }}
    .swagger-ui .topbar .download-url-wrapper input[type=text] {{
      border: 1px solid #475569;
      background: #0f172a;
      color: #38bdf8;
    }}
    .swagger-ui .info {{
      margin: 20px 0;
    }}
    .swagger-ui .info .title {{
      color: #38bdf8;
    }}
    .swagger-ui .scheme-container {{
      background: #1e293b;
      box-shadow: none;
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js" charset="UTF-8"></script>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js" charset="UTF-8"></script>
  <script>
    window.onload = function() {{
      window.ui = SwaggerUIBundle({{
        url: "{openapi_url}",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout"
      }});
    }};
  </script>
</body>
</html>
"""


class OpenAPISchemaValidator:
    """
    OpenAPI 3.1 Request / Response payload validation middleware engine.
    Validates JSON bodies against registered component schemas.
    """

    # Mapping from endpoint route pattern & HTTP method to schema component name
    REQUEST_SCHEMA_MAP = {
        ("POST", "/api/v1/mobile/scan"): "MobileScanRequest",
        ("POST", "/api/mobile/scan"): "MobileScanRequest",
        ("POST", "/api/v1/compliance/correct"): "CorrectionRequest",
        ("POST", "/api/compliance/correct"): "CorrectionRequest",
        ("POST", "/api/v1/compliance/einvoice/submit"): "EInvoiceRequest",
        ("POST", "/api/compliance/einvoice/submit"): "EInvoiceRequest",
        ("POST", "/api/v1/compliance/mesh/sync"): "MeshSyncRequest",
        ("POST", "/api/compliance/mesh/sync"): "MeshSyncRequest",
    }

    RESPONSE_SCHEMA_MAP = {
        ("GET", "/api/v1/telemetry"): "TelemetryResponse",
        ("GET", "/api/telemetry"): "TelemetryResponse",
        ("GET", "/api/v2/telemetry"): "TelemetryResponseV2",
        ("GET", "/api/v1/compliance/summary"): "ComplianceSummaryResponse",
        ("GET", "/api/compliance/summary"): "ComplianceSummaryResponse",
        ("GET", "/api/v1/mobile/status"): "MobileStatusResponse",
        ("GET", "/api/mobile/status"): "MobileStatusResponse",
    }

    @classmethod
    def validate_request(cls, method: str, path: str, body: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates an incoming HTTP request JSON body against OpenAPI schema.
        Returns (is_valid, error_list).
        """
        key = (method.upper(), path)
        schema_name = cls.REQUEST_SCHEMA_MAP.get(key)

        if not schema_name:
            # Route does not require strict payload schema validation
            return True, []

        schemas = OPENAPI_SPEC.get("components", {}).get("schemas", {})
        schema = schemas.get(schema_name)
        if not schema:
            return True, []

        return cls._validate_dict_against_schema(body, schema, schema_name)

    @classmethod
    def validate_response(cls, method: str, path: str, status_code: int, body: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates an outgoing HTTP response JSON body against OpenAPI schema.
        Returns (is_valid, error_list).
        """
        if status_code >= 400:
            return True, []

        key = (method.upper(), path)
        schema_name = cls.RESPONSE_SCHEMA_MAP.get(key)
        if not schema_name:
            return True, []

        schemas = OPENAPI_SPEC.get("components", {}).get("schemas", {})
        schema = schemas.get(schema_name)
        if not schema:
            return True, []

        return cls._validate_dict_against_schema(body, schema, schema_name)

    @classmethod
    def _validate_dict_against_schema(cls, data: Any, schema: Dict[str, Any], context: str) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        if not isinstance(data, dict):
            return False, [f"Payload for '{context}' must be a JSON object, got {type(data).__name__}"]

        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required property '{field}' in '{context}'")

        # Check field types
        properties = schema.get("properties", {})
        for prop_name, prop_spec in properties.items():
            if prop_name in data:
                val = data[prop_name]
                expected_type = prop_spec.get("type")
                if expected_type and val is not None:
                    if expected_type == "string" and not isinstance(val, str):
                        errors.append(f"Property '{prop_name}' must be string, got {type(val).__name__}")
                    elif expected_type == "number" and not isinstance(val, (int, float)):
                        errors.append(f"Property '{prop_name}' must be number, got {type(val).__name__}")
                    elif expected_type == "integer" and not isinstance(val, int):
                        errors.append(f"Property '{prop_name}' must be integer, got {type(val).__name__}")
                    elif expected_type == "boolean" and not isinstance(val, bool):
                        errors.append(f"Property '{prop_name}' must be boolean, got {type(val).__name__}")
                    elif expected_type == "array" and not isinstance(val, list):
                        errors.append(f"Property '{prop_name}' must be array, got {type(val).__name__}")
                    elif expected_type == "object" and not isinstance(val, dict):
                        errors.append(f"Property '{prop_name}' must be object, got {type(val).__name__}")

        return len(errors) == 0, errors


class APIVersionRouter:
    """
    API Versioning Router managing v1, v2, legacy aliases, and header-based API versioning.
    """

    VERSION_ROUTES = {
        "/api/v1/telemetry": "/api/v1/telemetry",
        "/api/telemetry": "/api/v1/telemetry",
        "/api/v2/telemetry": "/api/v2/telemetry",
        "/api/v1/compliance/summary": "/api/v1/compliance/summary",
        "/api/compliance/summary": "/api/v1/compliance/summary",
        "/api/v1/compliance/telemetry": "/api/v1/compliance/telemetry",
        "/api/compliance/telemetry": "/api/v1/compliance/telemetry",
        "/api/v1/mobile/status": "/api/v1/mobile/status",
        "/api/mobile/status": "/api/v1/mobile/status",
        "/api/v1/mobile/scan": "/api/v1/mobile/scan",
        "/api/mobile/scan": "/api/v1/mobile/scan",
        "/api/v1/mobile/sync": "/api/v1/mobile/sync",
        "/api/mobile/sync": "/api/v1/mobile/sync",
        "/api/v1/compliance/correct": "/api/v1/compliance/correct",
        "/api/compliance/correct": "/api/v1/compliance/correct",
        "/api/v1/compliance/einvoice/submit": "/api/v1/compliance/einvoice/submit",
        "/api/compliance/einvoice/submit": "/api/v1/compliance/einvoice/submit",
        "/api/v1/compliance/mesh/sync": "/api/v1/compliance/mesh/sync",
        "/api/compliance/mesh/sync": "/api/v1/compliance/mesh/sync",
    }

    @classmethod
    def resolve_version_and_route(cls, raw_path: str, header_version: Optional[str] = None) -> Tuple[str, str]:
        """
        Resolves path and target API version ("v1" or "v2").
        Returns (canonical_path, api_version).
        """
        clean_path = raw_path.rstrip("/") if len(raw_path) > 1 else raw_path

        # Header override takes precedence if route is version-neutral
        api_version = "v1"
        if clean_path.startswith("/api/v2/"):
            api_version = "v2"
        elif header_version in ("2", "2.0", "v2"):
            api_version = "v2"

        canonical_path = cls.VERSION_ROUTES.get(clean_path, clean_path)
        return canonical_path, api_version
