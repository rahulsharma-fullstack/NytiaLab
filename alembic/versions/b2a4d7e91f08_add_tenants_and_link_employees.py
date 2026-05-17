"""Add tenants table and link employees to it.

Also widens employees.id (and the FK columns that reference it) from
String(10) to String(20) so the new tenant-prefixed IDs fit.

Revision ID: b2a4d7e91f08
Revises: 3adc8f74c2ea
Create Date: 2026-05-17 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2a4d7e91f08"
down_revision: str | Sequence[str] | None = "3adc8f74c2ea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Default tenants inserted as part of the upgrade. The first one
# (T_NYTIA_DEMO) is also the backfill target for the existing 8 employees.
_DEFAULT_TENANTS = [
    {"id": "T_NYTIA_DEMO", "name": "Nytia Demo"},
    {"id": "T_IBM", "name": "IBM"},
    {"id": "T_MICROSOFT", "name": "Microsoft"},
    {"id": "T_ACME", "name": "Acme Corp"},
]


def upgrade() -> None:
    """Upgrade schema."""

    # 1. Create the new tenants table.
    tenants_table = op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # 2. Seed the four default tenants. T_NYTIA_DEMO is the target for the
    #    backfill of existing employees.
    op.bulk_insert(tenants_table, _DEFAULT_TENANTS)

    # 3. Widen the FK columns that point at employees.id BEFORE altering
    #    employees.id itself. Postgres requires referencing columns to have
    #    the same type as the referenced column, so we widen them together.
    op.alter_column(
        "health_records",
        "employee_id",
        existing_type=sa.String(length=10),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
    op.alter_column(
        "recommendations",
        "employee_id",
        existing_type=sa.String(length=10),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
    op.alter_column(
        "employees",
        "id",
        existing_type=sa.String(length=10),
        type_=sa.String(length=20),
        existing_nullable=False,
    )

    # 4. Add the tenant_id column to employees as NULLABLE first so the
    #    existing rows survive the schema change.
    op.add_column(
        "employees",
        sa.Column("tenant_id", sa.String(length=20), nullable=True),
    )

    # 5. Backfill the existing 8 employees to the demo tenant.
    op.execute("UPDATE employees SET tenant_id = 'T_NYTIA_DEMO' WHERE tenant_id IS NULL")

    # 6. Now we can flip the column to NOT NULL.
    op.alter_column(
        "employees",
        "tenant_id",
        existing_type=sa.String(length=20),
        nullable=False,
    )

    # 7. Add the foreign key constraint and the lookup index.
    op.create_foreign_key(
        "fk_employees_tenant",
        "employees",
        "tenants",
        ["tenant_id"],
        ["id"],
    )
    op.create_index("idx_employees_tenant_id", "employees", ["tenant_id"])


def downgrade() -> None:
    """Reverse the upgrade.

    The legacy `employees.tenant` string column is not touched on either
    side, so it stays exactly as it was before this migration.
    """

    # WARNING: This downgrade narrows employees.id from String(20) back to String(10).
    # It will FAIL if any employee row has an id longer than 10 characters,
    # which is the case after scripts/seed_data.py inserts the IBM/Microsoft/Acme
    # employees (e.g. "E_IBM_001"). Before running this downgrade, delete those
    # rows or revert to the pre-seed state via:
    #   DELETE FROM health_records WHERE employee_id LIKE 'E\_%' ESCAPE '\';
    #   DELETE FROM recommendations WHERE employee_id LIKE 'E\_%' ESCAPE '\';
    #   DELETE FROM employees WHERE id LIKE 'E\_%' ESCAPE '\';

    # 1. Drop the index and FK so the column can come off.
    op.drop_index("idx_employees_tenant_id", table_name="employees")
    op.drop_constraint("fk_employees_tenant", "employees", type_="foreignkey")

    # 2. Drop the tenant_id column from employees.
    op.drop_column("employees", "tenant_id")

    # 3. Narrow the FK columns back to String(10). We must shrink the
    #    referencing columns before shrinking the referenced PK, same as on
    #    the way up but in reverse order.
    op.alter_column(
        "employees",
        "id",
        existing_type=sa.String(length=20),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
    op.alter_column(
        "health_records",
        "employee_id",
        existing_type=sa.String(length=20),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
    op.alter_column(
        "recommendations",
        "employee_id",
        existing_type=sa.String(length=20),
        type_=sa.String(length=10),
        existing_nullable=False,
    )

    # 4. Drop the tenants table last.
    op.drop_table("tenants")
