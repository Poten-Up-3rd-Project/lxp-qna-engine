from datetime import datetime, timezone

import httpx
import pytest

from lxp_qna_engine.cli import process_pending
from lxp_qna_engine.config.settings import Settings, Callback, LLM
from lxp_qna_engine.domain.models import Envelope, QnaCreatedPayload, Course, Section, Lecture, Qna
from lxp_qna_engine.infrastructure.store_sqlite import Store


@pytest.mark.asyncio
async def test_end_to_end_like(monkeypatch, tmp_path):
    cfg = Settings()
    cfg.llm = LLM(provider="openai", model="gpt-4o-mini", temperature=0.0, max_tokens=64)
    cfg.callback = Callback(base="http://example.com/api-v1/qna", timeout_seconds=5)

    dsn = f"sqlite+pysqlite:///{tmp_path}/qna.db"
    store = Store(dsn)

    env = Envelope(
        eventId="evt-999",
        occurredAt=datetime.now(timezone.utc),
        payload=QnaCreatedPayload(
            course=Course(uuid="c", title="T"),
            section=Section(uuid="s", title="S"),
            lecture=Lecture(uuid="l", title="L"),
            qna=Qna(id="qna-999", authorId="u", title="Q", content="C", createdAt=datetime.now(timezone.utc)),
        ),
    )
    await store.save_pending(env)

    # Fix LLM answer
    monkeypatch.setattr("lxp_qna_engine.application.llm_answer.generate_answer", lambda _cfg, _env: "OK")

    async def fake_post(url, headers=None, json=None):
        class R:
            status_code = 201

            def raise_for_status(self):
                return None

        assert url.endswith("/qna-999/answers")
        assert headers.get("Idempotency-Key") == "evt-999"
        assert json["answerText"] == "OK"
        return R()

    class FakeClient:
        async def __aenter__(self): return self

        async def __aexit__(self, *a): return False

        post = staticmethod(fake_post)

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: FakeClient())

    await process_pending(store, cfg)
    assert (await store.load_unprocessed(limit=10)) == []
