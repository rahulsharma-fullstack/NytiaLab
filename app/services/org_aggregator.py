"""Workforce-level aggregation for the org-level recommender.

Given a tenant, this service rolls every employee's health records up into
two ranked lists:

- per-condition pressure: how heavily each chronic condition weighs on this
  workforce, plus suffering / at-risk counts and percentages.
- per-factor pressure: same idea for contributing factors.

The pressure score uses the SAME severity and status weights as the
per-employee recommender (`app/services/scoring.py`). We reuse them rather
than redefining so the org-level math stays consistent with the per-employee
math: an org pressure is just the per-employee weighted match summed across
the workforce.

# Performance note
# ----------------
# Current implementation uses Python aggregation: pull every employee row
# (with health records eager-loaded), then iterate in Python. Suitable for
# tenants up to ~1000 employees. For larger tenants, refactor to SQL
# GROUP BY with indexes on health_records (employee_id is already indexed
# via the FK; factor and health_condition already have their own indexes).
#
# Demo data is 30 employees per tenant so this is fine for now.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import Employee, HealthRecord
from app.repositories.employee_repo import EmployeeRepository
from app.services.scoring import SEVERITY_WEIGHT, STATUS_WEIGHT


@dataclass
class DimensionPressure:
    """Population-level rollup for one factor or one condition.

    `name` is the DB-side label ("Mental Illness", "Stress", etc.).
    `pressure_score` is the sum of severity_weight * status_weight across every
    record that mentions this dimension for this tenant. Higher pressure means
    bigger workforce-wide problem.

    `suffering_count` and `at_risk_count` count *distinct employees* in each
    status, not total records. Two records on the same employee for the same
    factor only count once.
    """

    name: str
    suffering_count: int = 0
    at_risk_count: int = 0
    pressure_score: float = 0.0

    @property
    def total_affected(self) -> int:
        return self.suffering_count + self.at_risk_count

    def percent_affected(self, total_employees: int) -> float:
        if total_employees == 0:
            return 0.0
        return round(100.0 * self.total_affected / total_employees, 1)


@dataclass
class WorkforceProfile:
    """The aggregated view of one tenant's workforce."""

    tenant_id: str
    total_employees: int
    conditions: list[DimensionPressure] = field(default_factory=list)
    factors: list[DimensionPressure] = field(default_factory=list)


# ----- internal helpers -----


def _weight_for(record: HealthRecord) -> float:
    """severity_weight * status_weight, matching the per-employee scoring math.

    Unknown severity or status fall back to 1.0 so we never crash on dirty
    data, but the CHECK constraints on the table make this defensive only.
    """
    sev_w = SEVERITY_WEIGHT.get(record.severity, 1.0)
    stat_w = STATUS_WEIGHT.get(record.status, 1.0)
    return sev_w * stat_w


def _accumulate(
    bucket: dict[str, DimensionPressure],
    name: str,
    record: HealthRecord,
    seen_employees: dict[str, set[str]],
    employee_id: str,
) -> None:
    """Add one record's contribution to a (factor or condition) bucket.

    `seen_employees[name]` tracks which employee ids have already been
    counted in the suffering / at_risk counters for this dimension, so a
    second record on the same employee does not double-count the head.

    Mixed-status edge case: if the same employee has both Suffering and At
    Risk records for the same dimension, the first record encountered
    determines which head count they go in. The pressure score still counts
    all records (so total severity * status weighting is correct), only the
    "how many distinct people" tally is first-seen-wins.

    Production-grade alternative: pick the most recent record per
    (employee, dimension) and use its status. Left as a future change so
    Nouridine can decide which behavior fits the dashboard semantics.
    """
    pressure = bucket.setdefault(name, DimensionPressure(name=name))
    pressure.pressure_score += _weight_for(record)

    employees_for_dim = seen_employees.setdefault(name, set())
    if employee_id not in employees_for_dim:
        employees_for_dim.add(employee_id)
        if record.status == "Suffering":
            pressure.suffering_count += 1
        elif record.status == "At Risk":
            pressure.at_risk_count += 1


def aggregate_from_employees(
    tenant_id: str,
    employees: Iterable[Employee],
) -> WorkforceProfile:
    """Pure-Python aggregation. Takes an iterable of Employee rows with their
    `.health_records` already loaded and returns a `WorkforceProfile`.

    Separated from `aggregate_workforce` so it can be unit-tested with stub
    objects and so callers that already hold employees in memory do not have
    to round-trip through the repository.
    """
    employees_list = list(employees)
    total_employees = len(employees_list)

    condition_bucket: dict[str, DimensionPressure] = {}
    factor_bucket: dict[str, DimensionPressure] = {}
    seen_by_condition: dict[str, set[str]] = {}
    seen_by_factor: dict[str, set[str]] = {}

    for employee in employees_list:
        for record in employee.health_records:
            _accumulate(
                condition_bucket,
                record.health_condition,
                record,
                seen_by_condition,
                employee.id,
            )
            _accumulate(
                factor_bucket,
                record.factor,
                record,
                seen_by_factor,
                employee.id,
            )

    conditions = sorted(
        (dp for dp in condition_bucket.values() if dp.total_affected > 0),
        key=lambda dp: dp.pressure_score,
        reverse=True,
    )
    factors = sorted(
        (dp for dp in factor_bucket.values() if dp.total_affected > 0),
        key=lambda dp: dp.pressure_score,
        reverse=True,
    )

    # Round pressure_score to 2 decimals for stable comparisons in tests and
    # for clean JSON output downstream.
    for dp in conditions:
        dp.pressure_score = round(dp.pressure_score, 2)
    for dp in factors:
        dp.pressure_score = round(dp.pressure_score, 2)

    return WorkforceProfile(
        tenant_id=tenant_id,
        total_employees=total_employees,
        conditions=conditions,
        factors=factors,
    )


# ----- public entry point -----


def aggregate_workforce(tenant_id: str, db: Session) -> WorkforceProfile:
    """Fetch every employee for the tenant (with health records eager-loaded)
    and return the aggregated `WorkforceProfile`.

    Does NOT verify that the tenant exists. That responsibility lives in
    `TenantService.get_tenant` and the orchestrator service that calls this.
    An unknown tenant id will simply return an empty workforce here.
    """
    employees = EmployeeRepository(db).get_all_by_tenant(tenant_id)
    return aggregate_from_employees(tenant_id, employees)
