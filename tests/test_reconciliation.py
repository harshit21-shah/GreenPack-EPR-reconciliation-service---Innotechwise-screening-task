from datetime import datetime, timezone

from app.reconciliation import reconcile
from app.schemas import DeclarationRecord


def make_declaration(quantities: dict[str, float]) -> DeclarationRecord:
    return DeclarationRecord(
        record_id="rec-1",
        producer_id="GREENPACK-001",
        month="2026-04",
        declared_quantities_kg=quantities,
        created_at=datetime.now(timezone.utc),
    )


def test_reconcile_flags_variance_above_five_percent():
    declaration = make_declaration(
        {
            "rigid_plastic": 12000,
            "flexible_plastic": 8500,
            "multilayer_plastic": 3200,
        }
    )

    rows = reconcile(
        declaration,
        {
            "rigid_plastic": 11800,
            "flexible_plastic": 9100,
            "multilayer_plastic": 3150,
        },
    )

    by_category = {row.category: row for row in rows}
    assert by_category["flexible_plastic"].flagged is True
    assert by_category["rigid_plastic"].flagged is False
    assert by_category["multilayer_plastic"].flagged is False


def test_reconcile_flags_declared_quantity_when_procured_is_zero():
    declaration = make_declaration(
        {
            "rigid_plastic": 25,
            "flexible_plastic": 0,
            "multilayer_plastic": 0,
        }
    )

    rows = reconcile(
        declaration,
        {
            "rigid_plastic": 0,
            "flexible_plastic": 0,
            "multilayer_plastic": 0,
        },
    )

    by_category = {row.category: row for row in rows}
    assert by_category["rigid_plastic"].variance_percent == 100
    assert by_category["rigid_plastic"].flagged is True
    assert by_category["flexible_plastic"].variance_percent == 0
    assert by_category["flexible_plastic"].flagged is False
