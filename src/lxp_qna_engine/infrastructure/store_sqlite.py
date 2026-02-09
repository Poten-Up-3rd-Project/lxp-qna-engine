from __future__ import annotations

from typing import Iterable, List, Optional

import orjson
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from ..domain.models import Envelope


class Store:
    def __init__(self, dsn: str = "sqlite+pysqlite:///:memory:") -> None:
        self._engine: Engine = create_engine(
            dsn,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if dsn.endswith(":memory:") else None,
        )
        self._init_schema()

    def _init_schema(self) -> None:
        with self._engine.begin() as conn:
            conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS pending_qna (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    envelope_json BLOB NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                """
            )

    async def save_pending(self, env: Envelope) -> None:
        js = orjson.dumps(env.model_dump(mode="json"))
        with self._engine.begin() as conn:
            conn.exec_driver_sql(
                """
                INSERT OR IGNORE INTO pending_qna (id, event_id, occurred_at, envelope_json, status)
                VALUES (:id, :event_id, :occurred_at, :envelope_json, 'PENDING')
                """,
                {
                    "id": env.payload.qna.id,
                    "event_id": env.eventId,
                    "occurred_at": env.occurredAt.isoformat(),
                    "envelope_json": js,
                },
            )

    async def load_unprocessed(self, limit: int = 100) -> List[Envelope]:
        rows: Iterable = []
        with self._engine.begin() as conn:
            rows = conn.exec_driver_sql(
                "SELECT envelope_json FROM pending_qna WHERE status='PENDING' LIMIT :limit",
                {"limit": limit},
            ).fetchall()
        return [Envelope.model_validate(orjson.loads(r[0])) for r in rows]

    async def mark_processed(self, qna_id: str) -> None:
        with self._engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE pending_qna SET status='DONE', updated_at=datetime('now') WHERE id=:id",
                {"id": qna_id},
            )

    async def mark_failed(self, qna_id: str, error: Optional[str] = None) -> None:
        with self._engine.begin() as conn:
            conn.exec_driver_sql(
                """
                UPDATE pending_qna
                SET status='FAILED', attempts=attempts+1, last_error=:err, updated_at=datetime('now')
                WHERE id=:id
                """,
                {"id": qna_id, "err": error or ""},
            )
