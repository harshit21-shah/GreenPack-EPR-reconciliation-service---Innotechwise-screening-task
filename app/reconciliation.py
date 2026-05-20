import csv
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from app.schemas import CategoryReconciliation, DeclarationRecord, PLASTIC_CATEGORIES


@lru_cache(maxsize=4)
def _load_all_erp_rows(csv_path: str) -> tuple[tuple[str, str, str, float], ...]:
    rows = []
    with Path(csv_path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                (
                    row["producer_id"],
                    row["month"],
                    row["category"],
                    float(row["procured_kg"]),
                )
            )
    return tuple(rows)


def load_erp_feed(csv_path: Path, producer_id: str, month: str) -> Dict[str, float]:
    totals = {category: 0.0 for category in PLASTIC_CATEGORIES}
    for row_producer_id, row_month, category, procured_kg in _load_all_erp_rows(str(csv_path.resolve())):
        if row_producer_id == producer_id and row_month == month and category in totals:
            totals[category] += procured_kg
    return totals


def clear_erp_cache() -> None:
    _load_all_erp_rows.cache_clear()


def calculate_variance_percent(declared: float, procured: float) -> float:
    if procured == 0:
        return 0.0 if declared == 0 else 100.0
    return abs(declared - procured) / procured * 100


def reconcile(
    declaration: DeclarationRecord,
    erp_quantities: Dict[str, float],
    tolerance_percent: float = 5.0,
) -> List[CategoryReconciliation]:
    results = []
    for category in sorted(PLASTIC_CATEGORIES):
        declared = float(declaration.declared_quantities_kg[category])
        procured = float(erp_quantities.get(category, 0.0))
        variance = declared - procured
        variance_percent = calculate_variance_percent(declared, procured)
        results.append(
            CategoryReconciliation(
                category=category,
                declared_kg=round(declared, 2),
                procured_kg=round(procured, 2),
                variance_kg=round(variance, 2),
                variance_percent=round(variance_percent, 2),
                flagged=variance_percent > tolerance_percent,
            )
        )
    return results
