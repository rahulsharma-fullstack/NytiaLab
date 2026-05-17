"""Tests for the org-level workforce aggregator.

These tests use stub objects (no DB) because `aggregate_from_employees` is
pure Python over duck-typed inputs. We exercise:

- empty tenant
- single employee + single record
- multi-employee aggregation
- severity * status weight application
- Suffering vs At Risk per-employee split
- sort order on pressure_score
- de-dup of suffering / at-risk counts when an employee has multiple records
  on the same dimension
"""

from dataclasses import dataclass, field

from app.services.org_aggregator import aggregate_from_employees
from app.services.scoring import SEVERITY_WEIGHT, STATUS_WEIGHT


@dataclass
class StubHealthRecord:
    factor: str
    health_condition: str
    severity: str
    status: str


@dataclass
class StubEmployee:
    id: str
    health_records: list = field(default_factory=list)


# ----- empty -----


def test_aggregate_empty_tenant_returns_empty_profile():
    profile = aggregate_from_employees("T_EMPTY", [])

    assert profile.tenant_id == "T_EMPTY"
    assert profile.total_employees == 0
    assert profile.conditions == []
    assert profile.factors == []


def test_aggregate_employees_with_no_records_returns_empty_dimensions():
    """Employees count toward `total_employees`, but if they have no records
    there is nothing to aggregate."""
    employees = [
        StubEmployee(id="E_T_001", health_records=[]),
        StubEmployee(id="E_T_002", health_records=[]),
    ]

    profile = aggregate_from_employees("T_TEST", employees)

    assert profile.total_employees == 2
    assert profile.conditions == []
    assert profile.factors == []


# ----- single employee, single record -----


def test_single_employee_single_record_produces_one_dimension_each():
    """One record contributes one entry on the conditions side and one on the
    factors side. Counts are 1, percent is 100."""
    employee = StubEmployee(
        id="E_T_001",
        health_records=[
            StubHealthRecord(
                factor="Stress",
                health_condition="Mental Illness",
                severity="Important",
                status="At Risk",
            )
        ],
    )

    profile = aggregate_from_employees("T_TEST", [employee])

    assert profile.total_employees == 1

    assert len(profile.conditions) == 1
    cond = profile.conditions[0]
    assert cond.name == "Mental Illness"
    assert cond.suffering_count == 0
    assert cond.at_risk_count == 1
    assert cond.total_affected == 1
    assert cond.percent_affected(1) == 100.0

    assert len(profile.factors) == 1
    factor = profile.factors[0]
    assert factor.name == "Stress"
    assert factor.suffering_count == 0
    assert factor.at_risk_count == 1


# ----- weight math -----


def test_pressure_score_uses_severity_times_status_weights():
    """Pressure should equal SEVERITY_WEIGHT[sev] * STATUS_WEIGHT[stat]
    summed across matching records. For one record this is exactly that
    product, rounded to 2 decimals."""
    employee = StubEmployee(
        id="E_T_001",
        health_records=[
            StubHealthRecord(
                factor="Sleep",
                health_condition="Cardiovascular Disease",
                severity="Very Important",
                status="Suffering",
            )
        ],
    )

    profile = aggregate_from_employees("T_TEST", [employee])

    expected = SEVERITY_WEIGHT["Very Important"] * STATUS_WEIGHT["Suffering"]
    assert profile.conditions[0].pressure_score == round(expected, 2)
    assert profile.factors[0].pressure_score == round(expected, 2)


def test_suffering_record_outweighs_at_risk_record_on_same_dimension():
    """Two different employees, same condition. Suffering should produce a
    higher per-record contribution than At Risk."""
    suffering_emp = StubEmployee(
        id="E_T_001",
        health_records=[
            StubHealthRecord(
                factor="Sleep",
                health_condition="Mental Illness",
                severity="Important",
                status="Suffering",
            )
        ],
    )
    at_risk_emp = StubEmployee(
        id="E_T_002",
        health_records=[
            StubHealthRecord(
                factor="Sleep",
                health_condition="Mental Illness",
                severity="Important",
                status="At Risk",
            )
        ],
    )

    suffering_only = aggregate_from_employees("T_A", [suffering_emp]).conditions[0].pressure_score
    at_risk_only = aggregate_from_employees("T_B", [at_risk_emp]).conditions[0].pressure_score

    assert suffering_only > at_risk_only


# ----- multi-employee aggregation -----


def test_multi_employee_aggregation_sums_pressure():
    """Three employees, same condition, mixed severities and statuses.
    Pressure should equal the sum of the three (severity * status) products."""
    e1 = StubEmployee(
        id="E1",
        health_records=[
            StubHealthRecord(
                factor="Stress",
                health_condition="Mental Illness",
                severity="Very Important",
                status="Suffering",
            )
        ],
    )
    e2 = StubEmployee(
        id="E2",
        health_records=[
            StubHealthRecord(
                factor="Stress",
                health_condition="Mental Illness",
                severity="Important",
                status="At Risk",
            )
        ],
    )
    e3 = StubEmployee(
        id="E3",
        health_records=[
            StubHealthRecord(
                factor="Stress",
                health_condition="Mental Illness",
                severity="Important",
                status="Suffering",
            )
        ],
    )

    profile = aggregate_from_employees("T_TEST", [e1, e2, e3])
    cond = profile.conditions[0]

    expected = (
        SEVERITY_WEIGHT["Very Important"] * STATUS_WEIGHT["Suffering"]
        + SEVERITY_WEIGHT["Important"] * STATUS_WEIGHT["At Risk"]
        + SEVERITY_WEIGHT["Important"] * STATUS_WEIGHT["Suffering"]
    )
    assert cond.pressure_score == round(expected, 2)
    assert cond.suffering_count == 2  # E1 and E3
    assert cond.at_risk_count == 1  # E2
    assert cond.total_affected == 3
    assert cond.percent_affected(3) == 100.0


# ----- de-dup of head counts -----


def test_duplicate_records_on_same_employee_do_not_inflate_head_counts():
    """One employee, two Suffering records for the same condition. The
    suffering_count must remain 1 (we count employees, not rows). The
    pressure_score does still sum across both records, by design."""
    employee = StubEmployee(
        id="E_T_001",
        health_records=[
            StubHealthRecord(
                factor="Stress",
                health_condition="Mental Illness",
                severity="Important",
                status="Suffering",
            ),
            StubHealthRecord(
                factor="Stress",
                health_condition="Mental Illness",
                severity="Important",
                status="Suffering",
            ),
        ],
    )

    profile = aggregate_from_employees("T_TEST", [employee])
    cond = profile.conditions[0]

    assert cond.suffering_count == 1
    assert cond.at_risk_count == 0
    assert cond.total_affected == 1


def test_mixed_status_on_same_employee_uses_first_seen_status_for_head_count():
    """If an employee has both a Suffering record and an At Risk record on
    the same dimension, the head count goes to whichever status we saw first
    (and only once). This documents the current behavior so future changes
    are intentional."""
    employee = StubEmployee(
        id="E_T_001",
        health_records=[
            StubHealthRecord(
                factor="Stress",
                health_condition="Mental Illness",
                severity="Important",
                status="Suffering",
            ),
            StubHealthRecord(
                factor="Stress",
                health_condition="Mental Illness",
                severity="Important",
                status="At Risk",
            ),
        ],
    )

    profile = aggregate_from_employees("T_TEST", [employee])
    cond = profile.conditions[0]
    assert cond.suffering_count + cond.at_risk_count == 1
    assert cond.total_affected == 1


# ----- sort order -----


def test_conditions_and_factors_sorted_by_pressure_descending():
    """Two conditions with different total pressure should come out
    highest-first."""
    e1 = StubEmployee(
        id="E1",
        health_records=[
            StubHealthRecord(
                factor="Stress",
                health_condition="Mental Illness",
                severity="Very Important",
                status="Suffering",
            ),
            StubHealthRecord(
                factor="Stress",
                health_condition="Mental Illness",
                severity="Very Important",
                status="Suffering",
            ),
        ],
    )
    e2 = StubEmployee(
        id="E2",
        health_records=[
            StubHealthRecord(
                factor="Movement",
                health_condition="Osteoporosis",
                severity="Important",
                status="At Risk",
            )
        ],
    )

    profile = aggregate_from_employees("T_TEST", [e1, e2])

    assert [c.name for c in profile.conditions] == ["Mental Illness", "Osteoporosis"]
    assert [f.name for f in profile.factors] == ["Stress", "Movement"]
    assert profile.conditions[0].pressure_score > profile.conditions[1].pressure_score


# ----- zero-pressure exclusion -----


def test_dimensions_with_zero_affected_are_excluded_from_output():
    """An employee with no records contributes nothing to either list, even if
    other employees in the same tenant have records. (Covered indirectly above
    but worth pinning explicitly.)"""
    e_quiet = StubEmployee(id="E_T_001", health_records=[])
    e_noisy = StubEmployee(
        id="E_T_002",
        health_records=[
            StubHealthRecord(
                factor="Sleep",
                health_condition="Mental Illness",
                severity="Important",
                status="At Risk",
            )
        ],
    )

    profile = aggregate_from_employees("T_TEST", [e_quiet, e_noisy])
    assert {c.name for c in profile.conditions} == {"Mental Illness"}
    assert {f.name for f in profile.factors} == {"Sleep"}
    assert profile.total_employees == 2
