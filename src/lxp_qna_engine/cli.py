from __future__ import annotations

import asyncio
import logging
import os
import platform
from datetime import datetime, timezone

import structlog
import uvloop
from fastapi import FastAPI, Request
from pydantic import BaseModel
from structlog import get_logger

from .adapters.http_callback import post_callback
from .adapters.mq_consumer import consume_and_buffer
from .application.llm_answer import generate_answer
from .application.scheduling import build_scheduler, add_cron_jobs
from .config.settings import Settings
from .infrastructure.store_sqlite import Store

# logging setup
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = get_logger()


class HealthResponse(BaseModel):
    """헬스체크 응답 모델."""

    status: str = "UP"
    version: str = "0.1.0"
    uptime_seconds: float | None = None


class InfoResponse(BaseModel):
    """애플리케이션 정보 응답 모델 (Spring Actuator /info 대응)."""

    app: dict
    python: str
    start_time: str | None = None


async def process_pending(store: Store, cfg: Settings):
    pending = await store.load_unprocessed(limit=200)
    for env in pending:
        try:
            answer = generate_answer(cfg.llm, env)
            await post_callback(cfg.callback, env, answer)
            await store.mark_processed(env.payload.qna.id)
            logger.info("answered", eventId=env.eventId, qnaId=env.payload.qna.id)
        except Exception as e:
            await store.mark_failed(env.payload.qna.id, str(e))
            logger.error("failed", eventId=env.eventId, qnaId=env.payload.qna.id, error=str(e))


async def main_async():
    cfg = Settings()
    logging.basicConfig(level=getattr(logging, cfg.log_level.upper(), logging.INFO))

    db_dsn = os.getenv("DB_DSN", "sqlite+pysqlite:///./qna.db")
    store = Store(db_dsn)

    # Startup configuration log (no secrets)
    logger.info(
        "startup",
        db_dsn=db_dsn,
        immediate=cfg.scheduling.immediate,
        cron_1=cfg.scheduling.cron_1,
        cron_2=cfg.scheduling.cron_2,
        timezone=cfg.scheduling.timezone,
        mq_url=cfg.messaging.url,
        mq_exchange=cfg.messaging.exchange,
        mq_routing_key=cfg.messaging.routing_key,
        mq_queue=cfg.messaging.queue,
        callback_base=cfg.callback.base,
        llm_provider=cfg.llm.provider,
        llm_model=cfg.llm.model,
        llm_temperature=cfg.llm.temperature,
        llm_max_tokens=cfg.llm.max_tokens,
        log_level=cfg.log_level,
    )

    scheduler = build_scheduler(cfg.scheduling)
    add_cron_jobs(scheduler, cfg.scheduling, lambda store: process_pending(store, cfg), store=store)
    scheduler.start()

    tasks = []
    # Rabbit consumer
    tasks.append(asyncio.create_task(
        consume_and_buffer(
            cfg.messaging.url,
            cfg.messaging.exchange,
            cfg.messaging.routing_key,
            cfg.messaging.queue,
            store,
        )
    ))

    # Optional immediate processing loop
    if cfg.scheduling.immediate:
        logger.info("immediate_loop.enabled", interval_seconds=5)

        async def immediate_loop():
            while True:
                await process_pending(store, cfg)
                await asyncio.sleep(5)

        tasks.append(asyncio.create_task(immediate_loop()))

    await asyncio.gather(*tasks)


def main():
    uvloop.install()
    asyncio.run(main_async())


def app():  # uvicorn --factory
    uvloop.install()
    loop = asyncio.get_event_loop()
    loop.create_task(main_async())

    f = FastAPI()
    # record process start time (timezone-aware)
    f.state.start_time = datetime.now(timezone.utc)

    @f.get("/healthz")
    async def healthz():
        return {"ok": True, "now": datetime.utcnow().isoformat()}

    @f.get("/health", response_model=HealthResponse)
    async def health_check(request: Request) -> HealthResponse:
        """헬스체크 엔드포인트 (k8s liveness/readiness probe 대응)."""
        start_time: datetime | None = getattr(request.app.state, "start_time", None)
        uptime = None
        if start_time:
            uptime = (datetime.now(timezone.utc) - start_time).total_seconds()
        return HealthResponse(uptime_seconds=uptime)

    @f.get("/info", response_model=InfoResponse)
    async def app_info(request: Request) -> InfoResponse:
        """애플리케이션 메타 정보 엔드포인트 (Spring Actuator /info 대응)."""
        start_time: datetime | None = getattr(request.app.state, "start_time", None)
        return InfoResponse(
            app={
                "name": "lxp-qna-engine",
                "version": "0.1.0",
                "description": "FastAPI QNA Engine for LXP",
            },
            python=platform.python_version(),
            start_time=start_time.isoformat() if start_time else None,
        )

    return f
