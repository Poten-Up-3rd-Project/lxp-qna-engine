from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Course(BaseModel):
    uuid: str
    title: str

class Section(BaseModel):
    uuid: str
    title: str

class Lecture(BaseModel):
    uuid: str
    title: str

class Qna(BaseModel):
    id: str
    authorId: str
    title: str
    content: str
    createdAt: datetime

class QnaCreatedPayload(BaseModel):
    course: Course
    section: Section
    lecture: Lecture
    qna: Qna

class Envelope(BaseModel):
    eventId: str
    occurredAt: datetime
    correlationId: Optional[str] = None
    causationId: Optional[str] = None
    payload: QnaCreatedPayload

class AnswerOut(BaseModel):
    answerText: str = Field(..., description="생성된 답변 텍스트")
    model: str
    answeredAt: datetime
    source: str = "lxp-qna-engine"
    eventId: str
