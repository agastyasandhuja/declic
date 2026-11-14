from typing import Annotated

from fastapi import APIRouter, Header, Request

from app.core.dependencies import CurrentUser
from app.modules.quizzes.schemas import (
    AnswerRequest,
    AnswerResponse,
    RecoveryRequest,
    RecoveryResponse,
)
from app.modules.recommendations.models import Identifier

router = APIRouter(prefix="/v1/quizzes", tags=["quizzes"])
progress_router = APIRouter(prefix="/v1/learning", tags=["learning"])


@router.post("/{quiz_instance_id}/answers", response_model=AnswerResponse)
def answer(
    quiz_instance_id: Identifier,
    body: AnswerRequest,
    request: Request,
    user: CurrentUser,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
):
    return request.app.state.quizzes.answer(user.user_id, quiz_instance_id, body, idempotency_key)


@router.post("/{quiz_instance_id}/recover", response_model=RecoveryResponse)
def recover(
    quiz_instance_id: Identifier, body: RecoveryRequest, request: Request, user: CurrentUser
):
    return request.app.state.quizzes.recover(user.user_id, quiz_instance_id, body)


@progress_router.get("/progress")
def progress(request: Request, user: CurrentUser):
    return request.app.state.quizzes.progress(user.user_id)
