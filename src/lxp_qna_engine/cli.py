from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

import structlog
import uvloop
from fastapi import FastAPI
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

    @f.get("/healthz")
    async def healthz():
        return {"ok": True, "now": datetime.utcnow().isoformat()}

    return f
