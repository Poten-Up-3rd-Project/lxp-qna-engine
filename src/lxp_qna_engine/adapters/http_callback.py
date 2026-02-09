from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..config.settings import Callback
from ..domain.models import Envelope, AnswerOut


async def post_callback(cfg: Callback, env: Envelope, answer_text: str) -> None:
    qna_id = env.payload.qna.id
    base = cfg.base.rstrip("/")
    # Ensure it starts with /api-v1/qna as requested
    if not base.endswith("/api-v1/qna"):
        base = base + "/api-v1/qna"
    url = f"{base}/{qna_id}/answers"

    # Diagnostics: log outgoing answer length and snippets
    ans_len = len(answer_text or "")
    head = (answer_text or "")[:64]
    tail = (answer_text or "")[-64:]
    from structlog import get_logger
    get_logger().info(
        "callback.outgoing",
        qnaId=qna_id,
        eventId=env.eventId,
        len=ans_len,
        head=head,
        tail=tail,
    )

    body = AnswerOut(
        answerText=answer_text,
        model="gemini",
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
