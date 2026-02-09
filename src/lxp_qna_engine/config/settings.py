import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Messaging:
    url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    exchange: str = os.getenv("RABBIT_EXCHANGE", "content.events")
    routing_key: str = os.getenv("RABBIT_ROUTING_KEY", "qna.created")
    queue: str = os.getenv("RABBIT_QUEUE", "lxp-qna-engine.qna-created")


@dataclass
class Scheduling:
    cron_1: str = os.getenv("CRON_1", "0 12 * * *")
    cron_2: str = os.getenv("CRON_2", "0 18 * * *")
    timezone: str = os.getenv("TIMEZONE", "Asia/Seoul")
    immediate: bool = os.getenv("IMMEDIATE_PROCESS", "false").lower() == "true"


@dataclass
class Callback:
    base: str = os.getenv("QNA_CALLBACK_BASE", "http://localhost:8080/api-v1/qna")
    timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))


@dataclass
class LLM:
    provider: str = os.getenv("LLM_PROVIDER", "openai").lower()
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key: str | None = os.getenv("OPENAI_API_KEY")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "512"))


@dataclass
class Settings:
    messaging: Messaging = field(default_factory=Messaging)
    scheduling: Scheduling = field(default_factory=Scheduling)
    callback: Callback = field(default_factory=Callback)
    llm: LLM = field(default_factory=LLM)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
