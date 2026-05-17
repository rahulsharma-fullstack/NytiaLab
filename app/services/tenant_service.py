"""Business logic for tenant operations."""

from sqlalchemy.orm import Session

from app.models import Tenant
from app.repositories import TenantRepository


class TenantNotFoundError(Exception):
    """Raised when a tenant ID does not exist in the database."""

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        super().__init__(f"Tenant {tenant_id!r} not found")


class TenantService:
    """Business logic for tenant-related operations."""

    def __init__(self, db: Session) -> None:
        self.repo = TenantRepository(db)

    def get_tenant(self, tenant_id: str) -> Tenant:
        """Fetch a tenant by ID. Raises TenantNotFoundError if missing."""
        tenant = self.repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError(tenant_id)
        return tenant

    def list_tenants(self) -> list[Tenant]:
        """Return every tenant ordered by id."""
        return self.repo.get_all()
