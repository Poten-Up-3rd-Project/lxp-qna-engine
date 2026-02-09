from __future__ import annotations

import asyncio
import json
import logging

import aio_pika
import aiormq
from pydantic import ValidationError

from ..domain.models import Envelope

logger = logging.getLogger(__name__)


async def _connect_with_retry(mq_url: str, *, max_delay: int = 30):
    delay = 1
    while True:
        try:
            return await aio_pika.connect_robust(mq_url)
        except (ConnectionRefusedError, aiormq.exceptions.AMQPConnectionError) as e:
            logger.warning("rabbit not ready, retrying", extra={"error": str(e), "delay": delay})
            await asyncio.sleep(delay)
            delay = min(max_delay, delay * 2)


async def consume_and_buffer(mq_url: str, exchange: str, routing_key: str, queue: str, store):
    connection = await _connect_with_retry(mq_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=32)
        ex = await channel.declare_exchange(exchange, aio_pika.ExchangeType.TOPIC, durable=True)
        q = await channel.declare_queue(queue, durable=True)
        await q.bind(ex, routing_key)

        async with q.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process(ignore_processed=True):
                    try:
                        body = json.loads(message.body)
                        env = Envelope.model_validate(body)
                        await store.save_pending(env)
                        logger.info("buffered", extra={"eventId": env.eventId, "qnaId": env.payload.qna.id})
                    except (json.JSONDecodeError, ValidationError):
                        logger.exception("invalid message, reject")
                        await message.reject(requeue=False)
