import json
import sqlite3
from pathlib import Path
from typing import Optional

from app.schemas import DeclarationIn, DeclarationRecord


class DeclarationStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS declarations (
                    record_id TEXT PRIMARY KEY,
                    producer_id TEXT NOT NULL,
                    month TEXT NOT NULL,
                    declared_quantities_kg TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(producer_id, month)
                )
                """
            )

    def save(self, declaration: DeclarationIn) -> DeclarationRecord:
        record = DeclarationRecord(**declaration.model_dump())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO declarations (
                    record_id, producer_id, month, declared_quantities_kg, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(producer_id, month) DO UPDATE SET
                    record_id = excluded.record_id,
                    declared_quantities_kg = excluded.declared_quantities_kg,
                    created_at = excluded.created_at
                """,
                (
                    record.record_id,
                    record.producer_id,
                    record.month,
                    json.dumps(record.declared_quantities_kg),
                    record.created_at.isoformat(),
                ),
            )
        return record

    def get(self, producer_id: str, month: str) -> Optional[DeclarationRecord]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT record_id, producer_id, month, declared_quantities_kg, created_at
                FROM declarations
                WHERE producer_id = ? AND month = ?
                """,
                (producer_id, month),
            ).fetchone()
        if row is None:
            return None
        return DeclarationRecord(
            record_id=row["record_id"],
            producer_id=row["producer_id"],
            month=row["month"],
            declared_quantities_kg=json.loads(row["declared_quantities_kg"]),
            created_at=row["created_at"],
        )
