"""The function-calling chatbot endpoint (docs/PROJECT_ARCHITECTURE.md §8).

Contains no query logic of its own everything real lives in chat_service.py, which this
file just calls and turns into an HTTP response.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatUnavailableError, run_chat

router = APIRouter(prefix="/chat")


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: DbSession) -> ChatResponse:
    # One question in, one real-data-grounded answer out. A missing/invalid Gemini key (or
    # any other reason Gemini can't be reached) is reported as a clear 503, never a crash.
    try:
        answer = run_chat(db, payload.message, [turn.model_dump() for turn in payload.history])
    except ChatUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return ChatResponse(answer=answer)
