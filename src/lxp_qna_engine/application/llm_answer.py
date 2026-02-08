from __future__ import annotations
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from ..domain.models import Envelope
from ..config.settings import LLM

SYSTEM_KO = (
    "너는 강의 QnA 도우미다. 제공된 컨텍스트를 근거로 친절하고 간결하게 한국어로 답하라. "
    "추측은 피하고, 필요한 경우 단계별 설명과 간단한 예시를 포함하라."
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_KO),
    ("system", "코스: {course_title}\n섹션: {section_title}\n강의: {lecture_title}"),
    ("human", "질문 제목: {q_title}\n질문 내용: {q_content}"),
])


def build_llm(cfg: LLM):
    if cfg.provider == "openai":
        return ChatOpenAI(model=cfg.model, temperature=cfg.temperature, max_tokens=cfg.max_tokens)
    raise ValueError(f"Unsupported LLM provider: {cfg.provider}")


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
