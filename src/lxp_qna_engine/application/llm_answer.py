from __future__ import annotations

import os
import warnings

# Suppress legacy SDK FutureWarning emitted by langchain_google_genai<4
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module=r"^langchain_google_genai\.chat_models$",
)

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from ..config.settings import LLM
from ..domain.models import Envelope

SYSTEM_KO = (
    "너는 강의 QnA 도우미다. 제공된 컨텍스트를 근거로 친절하고 간결하게 한국어로 답하라. "
    "추측은 피하고, 필요한 경우 단계별 설명과 간단한 예시를 포함하라.\n\n"
    "코스: {course_title}\n섹션: {section_title}\n강의: {lecture_title}"
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_KO),
    ("human", "질문 제목: {q_title}\n질문 내용: {q_content}"),
])


def build_llm(cfg: LLM):
    # Optional: enable LangSmith if key provided
    ls_key = os.getenv("LANGSMITH_API_KEY")
    if ls_key:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGSMITH_API_KEY", ls_key.strip())

    # Gemini only
    if cfg.provider not in ("gemini", "google", "google-genai", "googleai"):
        raise ValueError("Only Gemini provider is supported in this build. Set MODEL_PROVIDER=gemini.")

    gk = cfg.gemini_key or os.getenv("GEMINI_KEY")
    if not gk:
        raise ValueError("GEMINI_KEY is not set")
    os.environ["GOOGLE_API_KEY"] = gk.strip()
    return ChatGoogleGenerativeAI(
        model=cfg.model,
        temperature=cfg.temperature,
        max_output_tokens=cfg.max_tokens,
    )


def make_chain(llm):
    return PROMPT | llm | StrOutputParser()


def generate_answer(cfg: LLM, env: Envelope) -> str:
    llm = build_llm(cfg)
    chain = make_chain(llm)
    p = env.payload
    return chain.invoke({
        "course_title": p.course.title,
        "section_title": p.section.title,
        "lecture_title": p.lecture.title,
        "q_title": p.qna.title,
        "q_content": p.qna.content,
    })
