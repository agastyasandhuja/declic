from typing import Protocol

from app.modules.quizzes.schemas import QuizDefinition


class QuizReader(Protocol):
    def list_for_objective(self, user_id: str, objective_id: str) -> list[QuizDefinition]: ...


class EmptyQuizzes:
    def list_for_objective(self, user_id: str, objective_id: str) -> list[QuizDefinition]:
        return []
