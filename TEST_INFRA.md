# E2E Test Infra: Microinvest Bank Statement OCR & Delta Pro Accounting Automation

## Test Philosophy
- Opaque-box, requirement-driven validation.
- Derived strictly from `/Users/diokarabaz/orca/workspaces/2026-08-05/работно-пространство/.agents/ORIGINAL_REQUEST.md`.
- Methodology: Category-Partition + BVA + Pairwise Combinatorial + Real-World Workload Testing.

## Feature Inventory & Test Coverage Thresholds
| # | Feature | Source | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|--------|:------:|:------:|:------:|:------:|
| 1 | OCR & Line-Item Extraction (1.pdf) | R1 | 5 | 5 | ✓ | ✓ |
| 2 | Bulgarian Double-Entry Translation & XML | R2 | 5 | 5 | ✓ | ✓ |
| 3 | Microinvest Delta Pro VNC & SQL Import | R3 | 5 | 5 | ✓ | ✓ |
| 4 | C:\TRANSFER.LOG Audit Log Validation | R4 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test runner: `pytest` / Python 3 test harness
- Test location: `tests/e2e/test_e2e_pipeline.py`
- Pass/Fail criterion: 100% assertions pass, exit code 0.
