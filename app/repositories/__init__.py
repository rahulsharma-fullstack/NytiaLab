"""Repository layer — data access only."""

from app.repositories.employee_repo import EmployeeRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.tenant_repo import TenantRepository

__all__ = ["EmployeeRepository", "ProductRepository", "TenantRepository"]
