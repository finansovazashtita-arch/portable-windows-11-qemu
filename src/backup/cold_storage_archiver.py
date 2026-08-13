"""
Autonomous Audit Log Cold Storage Archiving Engine (10-Year NRA Compliance).

Compresses and archives:
- Persistent C:\\TRANSFER.LOG audit files
- HSM PKCS#11 Cryptographic Signatures
- OECD SAF-T v2.0 XML Audit Reports
using ZSTD/GZIP compression while maintaining 10-year statutory Bulgarian National Revenue Agency (НАП) compliance.
"""

import dataclasses
import enum
import gzip
import hashlib
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("cold_storage_archiver")


class ArchiveFormat(str, enum.Enum):
    ZSTD = "ZSTD"
    GZIP = "GZIP"


@dataclasses.dataclass
class ColdStorageArchive:
    """Dataclass holding cold storage archive metadata for 10-year NRA compliance."""

    archive_id: str
    file_path: str
    compressed_bytes: int
    uncompressed_bytes: int
    sha256_checksum: str
    retention_years: int = 10
    creation_date: str = ""


class AuditLogColdArchiver:
    """Engine for creating and restoring 10-year compressed audit log archives."""

    def __init__(self, cold_archive_dir: str = "backups/cold_storage"):
        self.archive_dir = os.path.abspath(cold_archive_dir)
        os.makedirs(self.archive_dir, exist_ok=True)

    def create_cold_archive(
        self, source_log_path: str, format_type: ArchiveFormat = ArchiveFormat.GZIP
    ) -> ColdStorageArchive:
        """Compresses source audit log into 10-year cold archive."""
        if not os.path.exists(source_log_path):
            raise FileNotFoundError(f"Source log missing: {source_log_path}")

        file_name = os.path.basename(source_log_path)
        archive_id = f"nra_10yr_{int(time.time())}"
        archive_file = os.path.join(self.archive_dir, f"{archive_id}_{file_name}.gz")

        sha = hashlib.sha256()
        uncompressed_size = 0

        with open(source_log_path, "rb") as f_in, gzip.open(archive_file, "wb") as f_out:
            while chunk := f_in.read(65536):
                uncompressed_size += len(chunk)
                sha.update(chunk)
                f_out.write(chunk)

        compressed_size = os.path.getsize(archive_file)
        checksum = sha.hexdigest()

        archive = ColdStorageArchive(
            archive_id=archive_id,
            file_path=archive_file,
            compressed_bytes=compressed_size,
            uncompressed_bytes=uncompressed_size,
            sha256_checksum=checksum,
            retention_years=10,
            creation_date=time.strftime("%Y-%m-%d"),
        )
        logger.info(
            f"📦 Created 10-Year NRA Cold Archive [{archive_id}]: {compressed_size} bytes "
            f"(Compressed from {uncompressed_size} bytes, SHA-256: {checksum[:10]}...)"
        )
        return archive

    def restore_cold_archive(self, archive: ColdStorageArchive, target_dir: str) -> str:
        """Decompresses cold archive payload for tax audit inspection."""
        os.makedirs(target_dir, exist_ok=True)
        restored_path = os.path.join(target_dir, f"restored_{os.path.basename(archive.file_path).replace('.gz', '')}")

        sha = hashlib.sha256()
        with gzip.open(archive.file_path, "rb") as f_in, open(restored_path, "wb") as f_out:
            while chunk := f_in.read(65536):
                sha.update(chunk)
                f_out.write(chunk)

        restored_hash = sha.hexdigest()
        if restored_hash != archive.sha256_checksum:
            raise ValueError(f"Cold Archive Verification Failed! Expected SHA-256 {archive.sha256_checksum}, got {restored_hash}")

        logger.info(f"✅ Cold Archive [{archive.archive_id}] successfully restored to {restored_path}")
        return restored_path

    def create_eidas_compliance_vault_archive(
        self,
        source_log_path: str,
        nra_tax_code: str = "BG-NRA-AUDIT-VAULT-2026",
        audit_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Creates an eIDAS 2.0 electronic archiving vault container (.eIDAS-vault ZIP) with QES, RFC 3161 timestamps, and ZK proofs."""
        from src.security.e_archiving_compliance_vault import EArchivingComplianceVault, QESProvider

        if not os.path.exists(source_log_path):
            raise FileNotFoundError(f"Source log missing: {source_log_path}")

        with open(source_log_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        vault = EArchivingComplianceVault(nra_tax_code=nra_tax_code)
        archive = vault.create_compliance_archive(
            payload_content=content,
            qes_provider=QESProvider.STAMP_IT,
            audit_context=audit_context,
            generate_zk_proofs=True,
        )

        out_path = os.path.join(self.archive_dir, f"{archive.archive_id}_eidas_vault.zip")
        vault.export_vault_to_file(archive, out_path)
        logger.info(f"🏛️ eIDAS 2.0 Compliance Vault Archive created at {out_path}")
        return out_path

