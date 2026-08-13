"""
Automated Financial Audit Trail & Tamper-Evident Blockchain Ledger Integration (Audit Ledger Integrity Guard).

Provides tamper-evident cryptographic hash chaining (SHA-256) of every accounting operation:
- Appends every journal entry into an append-only immutable hash chain
- Computes cryptographic SHA-256 block digest linking to previous block hash
- Detects any historical tampering, unauthorized alteration, or deletion of accounting entries
- Provides verification report for National Revenue Agency (НАП) tax auditors
"""

import dataclasses
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("audit_ledger_guard")


@dataclasses.dataclass
class AuditBlock:
    """Dataclass holding an immutable tamper-evident audit ledger block."""

    block_index: int
    timestamp: str
    entry_data: Dict[str, Any]
    previous_hash: str
    current_hash: str


class AuditLedgerIntegrityGuard:
    """Guard engine for cryptographic ledger integrity and SHA-256 hash chaining."""

    def __init__(self) -> None:
        self.chain: List[AuditBlock] = []
        self._create_genesis_block()

    def _create_genesis_block(self) -> None:
        """Creates the initial genesis block of the audit chain."""
        genesis_data = {"event": "GENESIS_AUDIT_BLOCK", "system": "FinansProtect Accounting"}
        prev_hash = "0" * 64
        block_hash = self.compute_block_hash(0, "1970-01-01T00:00:00Z", genesis_data, prev_hash)

        genesis_block = AuditBlock(
            block_index=0,
            timestamp="1970-01-01T00:00:00Z",
            entry_data=genesis_data,
            previous_hash=prev_hash,
            current_hash=block_hash,
        )
        self.chain.append(genesis_block)

    @classmethod
    def compute_block_hash(
        cls, block_index: int, timestamp: str, entry_data: Dict[str, Any], previous_hash: str
    ) -> str:
        """Computes SHA-256 hash over block index, timestamp, canonical JSON payload, and previous hash."""
        payload_str = json.dumps(entry_data, sort_keys=True, separators=(",", ":"))
        raw_str = f"{block_index}|{timestamp}|{payload_str}|{previous_hash}"
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def append_entry(self, entry_data: Dict[str, Any], timestamp_str: Optional[str] = None) -> AuditBlock:
        """Appends a new accounting journal entry to the tamper-evident chain."""
        if not timestamp_str:
            timestamp_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        previous_block = self.chain[-1]
        block_index = len(self.chain)
        previous_hash = previous_block.current_hash

        current_hash = self.compute_block_hash(block_index, timestamp_str, entry_data, previous_hash)
        new_block = AuditBlock(
            block_index=block_index,
            timestamp=timestamp_str,
            entry_data=entry_data,
            previous_hash=previous_hash,
            current_hash=current_hash,
        )
        self.chain.append(new_block)
        logger.info(f"🔗 Audit Ledger Block #{block_index} appended: Hash={current_hash[:16]}...")
        return new_block

    def verify_chain_integrity(self) -> Tuple[bool, Optional[str]]:
        """Verifies full cryptographic chain integrity from genesis block to tip."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # 1. Check previous hash linkage
            if current.previous_hash != previous.current_hash:
                err = f"Chain linkage broken at block #{i}: expected prev_hash {previous.current_hash}, got {current.previous_hash}"
                logger.error(f"🚨 {err}")
                return False, err

            # 2. Re-compute current hash
            expected_hash = self.compute_block_hash(
                current.block_index, current.timestamp, current.entry_data, current.previous_hash
            )
            if current.current_hash != expected_hash:
                err = f"Block data tampered at block #{i}: expected hash {expected_hash}, got {current.current_hash}"
                logger.error(f"🚨 {err}")
                return False, err

        return True, None

    def export_chain_summary(self) -> Dict[str, Any]:
        """Exports audit ledger summary for NRA compliance verification."""
        is_valid, err = self.verify_chain_integrity()
        return {
            "total_blocks": len(self.chain),
            "chain_valid": is_valid,
            "error": err,
            "tip_hash": self.chain[-1].current_hash if self.chain else None,
        }
