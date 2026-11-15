"""The one-pass dashboard breakdown (Phase 5 M2) gives exactly what the four original queries gave.

The reference queries below are the pre-M2 implementations, kept verbatim so any difference in
totals, values, risk levels, types or simulated days fails here.
"""

from decimal import Decimal

import pytest
from sqlalchemy import case, func, select

from app.models.enums import PredictionDecision, UserRole
from app.models.records import Prediction, Transaction
from app.repositories import reports

pytestmark = pytest.mark.database

PREDICT = "/api/v1/transactions/predict"
INPUTS = [
    {
        "amount": "9000000.00",
        "transaction_type": "TRANSFER",
        "step": 5,
        "destination_category": "customer",
    },
    {
        "amount": "5000000.00",
        "transaction_type": "CASH_OUT",
        "step": 50,
        "destination_category": "customer",
    },
    {
        "amount": "250000.00",
        "transaction_type": "TRANSFER",
        "step": 200,
        "destination_category": "customer",
    },
    {
        "amount": "1000000.00",
        "transaction_type": "TRANSFER",
        "step": 400,
        "destination_category": "customer",
    },
    {
        "amount": "100.00",
        "transaction_type": "PAYMENT",
        "step": 12,
        "destination_category": "merchant",
    },
    {
        "amount": "75.50",
        "transaction_type": "PAYMENT",
        "step": 49,
        "destination_category": "merchant",
    },
    {
        "amount": "12345.67",
        "transaction_type": "CASH_IN",
        "step": 300,
        "destination_category": "customer",
    },
    {
        "amount": "999.99",
        "transaction_type": "DEBIT",
        "step": 743,
        "destination_category": "customer",
    },
]
FLAGGED = Prediction.prediction == PredictionDecision.FLAG_FOR_REVIEW


def reference_totals(session, is_demo):
    row = session.execute(
        select(
            func.count(Prediction.id),
            func.count(case((FLAGGED, 1))),
            func.coalesce(func.sum(Transaction.amount), 0),
            func.coalesce(func.sum(case((FLAGGED, Transaction.amount))), 0),
        )
        .join(Transaction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
    ).one()
    return row[0], row[1], Decimal(row[2]), Decimal(row[3])


def reference_risk(session, is_demo):
    rows = session.execute(
        select(Prediction.risk_level, func.count())
        .join(Transaction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
        .group_by(Prediction.risk_level)
    )
    return {level.value: count for level, count in rows}


def reference_types(session, is_demo):
    rows = session.execute(
        select(Transaction.transaction_type, func.count(), func.count(case((FLAGGED, 1))))
        .join(Prediction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
        .group_by(Transaction.transaction_type)
    )
    return {name: {"analysed": total, "flagged": flags} for name, total, flags in rows}


def reference_days(session, is_demo):
    day = (Transaction.simulation_step // reports.HOURS_PER_DAY).label("day")
    rows = session.execute(
        select(day, func.count(), func.count(case((FLAGGED, 1))))
        .join(Prediction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
        .group_by(day)
        .order_by(day)
    )
    return [{"day": int(d), "analysed": total, "flagged": flags} for d, total, flags in rows]


@pytest.fixture
def stored(client, headers_for):
    analyst, demo = headers_for(UserRole.ANALYST), headers_for(UserRole.DEMO)
    for index, body in enumerate(INPUTS):
        assert client.post(PREDICT, headers=analyst, json=body).status_code == 201
        if index % 3 == 0:
            assert client.post(PREDICT, headers=demo, json=body).status_code == 201


@pytest.mark.parametrize("is_demo", [False, True])
def test_breakdown_equals_the_original_queries(stored, session, is_demo):
    breakdown = reports.model_flag_breakdown(session, is_demo)
    assert (breakdown.total, breakdown.flagged, breakdown.total_value, breakdown.flagged_value) == (
        reference_totals(session, is_demo)
    )
    assert breakdown.by_risk == reference_risk(session, is_demo)
    assert breakdown.by_type == reference_types(session, is_demo)
    assert breakdown.by_day == reference_days(session, is_demo)
    assert breakdown.total > 0 and breakdown.flagged > 0  # the comparison saw real data


def test_breakdown_of_an_empty_scope(session):
    breakdown = reports.model_flag_breakdown(session, False)
    assert (breakdown.total, breakdown.flagged) == (0, 0)
    assert breakdown.total_value == breakdown.flagged_value == Decimal(0)
    assert (breakdown.by_risk, breakdown.by_type, breakdown.by_day) == ({}, {}, [])


def test_public_helpers_still_answer_from_the_breakdown(stored, session):
    breakdown = reports.model_flag_breakdown(session, False)
    assert reports.risk_distribution(session, False) == breakdown.by_risk
    assert reports.type_distribution(session, False) == breakdown.by_type
    assert reports.flags_by_simulation_day(session, False) == breakdown.by_day
    assert reports.model_flag_totals(session, False)["total"] == breakdown.total
