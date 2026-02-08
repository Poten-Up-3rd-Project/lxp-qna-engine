import pytest
from datetime import datetime, timezone
from lxp_qna_engine.domain.models import Envelope, QnaCreatedPayload, Course, Section, Lecture, Qna
from lxp_qna_engine.infrastructure.store_sqlite import Store


def make_envelope() -> Envelope:
    return Envelope(
        eventId="evt-123",
        occurredAt=datetime.now(timezone.utc),
        payload=QnaCreatedPayload(
            course=Course(uuid="c-1", title="파이썬"),
            section=Section(uuid="s-1", title="기초"),
            lecture=Lecture(uuid="l-1", title="변수"),
            qna=Qna(id="qna-1", authorId="u-1", title="질문", content="내용", createdAt=datetime.now(timezone.utc)),
        ),
    )


@pytest.mark.asyncio
async def test_store_roundtrip(tmp_path):
    dsn = f"sqlite+pysqlite:///{tmp_path}/qna.db"
    store = Store(dsn)
    env = make_envelope()

    await store.save_pending(env)
    items = await store.load_unprocessed(limit=10)
    assert len(items) == 1
    assert items[0].payload.qna.id == "qna-1"
