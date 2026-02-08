from __future__ import annotations
from datetime import datetime, timezone
import httpx
from ..domain.models import Envelope, AnswerOut
from ..config.settings import Callback

async def post_callback(cfg: Callback, env: Envelope, answer_text: str) -> None:
    qna_id = env.payload.qna.id
    base = cfg.base.rstrip("/")
    # Ensure it starts with /api-v1/qna as requested
    if not base.endswith("/api-v1/qna"):
        base = base + "/api-v1/qna"
    url = f"{base}/{qna_id}/answers"

    body = AnswerOut(
        answerText=answer_text,
        model="openai",
        answeredAt=datetime.now(timezone.utc),
        eventId=env.eventId,
    ).model_dump(mode="json")

    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": env.eventId,
    }

    async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
        for i in range(3):
            r = await client.post(url, headers=headers, json=body)
            if r.status_code < 500:
                r.raise_for_status()
                return
        r.raise_for_status()
