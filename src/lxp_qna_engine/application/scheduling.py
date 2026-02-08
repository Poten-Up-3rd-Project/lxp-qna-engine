from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config.settings import Scheduling


def build_scheduler(cfg: Scheduling):
    scheduler = AsyncIOScheduler(timezone=cfg.timezone)
    return scheduler


def add_cron_jobs(scheduler: AsyncIOScheduler, cfg: Scheduling, job, *, store):
    t1 = CronTrigger.from_crontab(cfg.cron_1, timezone=cfg.timezone)
    t2 = CronTrigger.from_crontab(cfg.cron_2, timezone=cfg.timezone)
    scheduler.add_job(job, t1, kwargs={"store": store})
    scheduler.add_job(job, t2, kwargs={"store": store})
