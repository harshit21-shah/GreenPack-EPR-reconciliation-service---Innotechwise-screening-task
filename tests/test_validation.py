import pytest
from pydantic import ValidationError

from app.schemas import DeclarationIn


def test_declaration_rejects_negative_quantities():
    with pytest.raises(ValidationError):
        DeclarationIn(
            producer_id="GREENPACK-001",
            month="2026-04",
            declared_quantities_kg={
                "rigid_plastic": 12000,
                "flexible_plastic": -1,
                "multilayer_plastic": 3200,
            },
        )


def test_declaration_rejects_bad_month_format():
    with pytest.raises(ValidationError):
        DeclarationIn(
            producer_id="GREENPACK-001",
            month="April 2026",
            declared_quantities_kg={
                "rigid_plastic": 12000,
                "flexible_plastic": 8500,
                "multilayer_plastic": 3200,
            },
        )
