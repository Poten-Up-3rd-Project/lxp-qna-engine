import pytest
from datetime import datetime, timezone
from lxp_qna_engine.cli import process_pending
from lxp_qna_engine.config.settings import Settings, LLM, Callback
from lxp_qna_engine.infrastructure.store_sqlite import Store
from lxp_qna_engine.domain.models import Envelope, QnaCreatedPayload, Course, Section, Lecture, Qna


def env_one(qid="qna-1", eid="evt-123"):
    return Envelope(
        eventId=eid,
        occurredAt=datetime.now(timezone.utc),
        payload=QnaCreatedPayload(
            course=Course(uuid="c-1", title="파이썬"),
            section=Section(uuid="s-1", title="기초"),
            lecture=Lecture(uuid="l-1", title="변수"),
            qna=Qna(id=qid, authorId="u-1", title="질문", content="내용", createdAt=datetime.now(timezone.utc)),
        ),
    )


@pytest.mark.asyncio
async def test_process_pending_marks_done(monkeypatch, tmp_path):
    cfg = Settings()
    cfg.llm = LLM(provider="openai", model="gpt-4o-mini", temperature=0.0, max_tokens=64)
    cfg.callback = Callback(base="http://localhost:9999/api-v1/qna", timeout_seconds=5)

    dsn = f"sqlite+pysqlite:///{tmp_path}/qna.db"
    store = Store(dsn)
    await store.save_pending(env_one())

    # Mock LLM and callback
    monkeypatch.setattr("lxp_qna_engine.application.llm_answer.generate_answer", lambda _cfg, _env: "테스트 답변")
    calls = {"n": 0}

    async def fake_post_callback(_cfg, _env, _answer):
        calls["n"] += 1

    monkeypatch.setattr("lxp_qna_engine.adapters.http_callback.post_callback", fake_post_callback)

    await process_pending(store, cfg)

    assert calls["n"] == 1
    left = await store.load_unprocessed(limit=10)
    assert len(left) == 0
