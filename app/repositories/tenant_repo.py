"""Repository for Tenant database operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tenant


class TenantRepository:
    """Data access layer for tenants."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, tenant_id: str) -> Tenant | None:
        """Fetch a single tenant by its ID. Returns None if not found."""
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all(self) -> list[Tenant]:
        """Return every tenant ordered by id."""
        stmt = select(Tenant).order_by(Tenant.id)
        return list(self.db.execute(stmt).scalars().all())
