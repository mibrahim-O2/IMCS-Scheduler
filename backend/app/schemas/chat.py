"""Request/response schemas for the Phase 10 function-calling chatbot.

See docs/PROJECT_ARCHITECTURE.md §8.
"""

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    # One earlier message in this session's conversation, sent back so Gemini has context
    # for a follow-up question ("and on Wednesday?").
    role: str = Field(pattern="^(user|assistant)$")
    text: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
