"""
Security Package.
"""

from src.security.audit_ledger_guard import AuditBlock, AuditLedgerIntegrityGuard
from src.security.hsm_signer import CryptographicSignature, HSMAuditLogSigner, HSMKeyType
from src.security.infisical_vault import InfisicalVaultClient
from src.security.pq_mesh_signer import MeshAttestationDocument, MeshNodeIdentity, MeshSignatureChain, PQMeshCertificate, PQMeshSigner
from src.security.tenant_rbac import JWTSecurityManager, Permission, Tenant, User, UserRole

# Backward compatibility aliases
HSMSignature = CryptographicSignature
HSMSignerEngine = HSMAuditLogSigner
PQCLatticeAlgorithm = HSMKeyType
Role = UserRole
TenantContext = Tenant
TenantRBACEngine = JWTSecurityManager

__all__ = [
    "TenantRBACEngine",
    "JWTSecurityManager",
    "Tenant",
    "TenantContext",
    "UserRole",
    "Role",
    "Permission",
    "User",
    "InfisicalVaultClient",
    "HSMAuditLogSigner",
    "HSMSignerEngine",
    "CryptographicSignature",
    "HSMSignature",
    "HSMKeyType",
    "PQCLatticeAlgorithm",
    "AuditLedgerIntegrityGuard",
    "AuditBlock",
    "PQMeshSigner",
    "MeshNodeIdentity",
    "MeshAttestationDocument",
    "MeshSignatureChain",
    "PQMeshCertificate",
]

