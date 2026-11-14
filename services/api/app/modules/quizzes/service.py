from datetime import timedelta

from app.core import collections as tables
from app.core import idempotency
from app.core.database import Database, insert_ignore
from app.core.errors import APIError
from app.core.events import publish
from app.core.time import iso, new_id, utc_now
from app.modules.quizzes.schemas import AnswerRequest, QuizDefinition, RecoveryRequest
from app.modules.recommendations import repository as repo
from app.modules.recommendations.adapters import AcademicReader, VideoReader
from app.workers.queue import enqueue


class QuizService:
    def __init__(
        self, database: Database, academics: AcademicReader, videos: VideoReader, clock=utc_now
    ):
        self.database = database
        self.academics = academics
        self.videos = videos
        self.clock = clock

    def _instance(self, conn, user_id: str, instance_id: str, session_id: str):
        row = conn.find_one(
            tables.quiz_instances,
            {
                "$and": [
                    {"user_id": user_id},
                    {"session_id": session_id},
                    {"instance_id": instance_id},
                ]
            },
        )
        if row is None:
            raise APIError(404, "NOT_FOUND", "Quiz instance not found")
        return row

    def _unlock(self, conn, user_id: str, state: dict, instance_id: str, status: str):
        conn.update(
            tables.quiz_instances,
            {"$and": [{"instance_id": instance_id}, {"user_id": user_id}]},
            {"state": status},
        )
        state["pending_quiz_instance_id"] = None
        state["required_quiz_instance_id"] = None
        state["quiz_exposures"] = []
        state["last_active_at"] = iso(self.clock())
        repo.save_session(conn, user_id, state)
        return repo.invalidate_user_feeds(conn, user_id)[state["session_id"]]

    def answer(self, user_id: str, instance_id: str, body: AnswerRequest, key: str) -> dict:
        route = f"quizzes/{instance_id}/answers"
        request = body.model_dump(mode="json")
        now = self.clock()

        def operation(conn):
            instance = self._instance(conn, user_id, instance_id, body.session_id)
            cached = idempotency.lookup(conn, user_id, route, key, request)
            if cached is not None:
                return cached
            prior = conn.value(
                tables.attempts,
                "data",
                {"$and": [{"instance_id": instance_id}, {"user_id": user_id}]},
            )
            if prior:
                response = prior["response"]
                idempotency.remember(conn, user_id, route, key, request, response)
                return response
            state = repo.get_session(conn, user_id, body.session_id)
            if instance["state"] != "pending" or state["pending_quiz_instance_id"] != instance_id:
                raise APIError(
                    409, "QUIZ_NOT_PENDING", "Activate the reached quiz before answering"
                )
            definition = QuizDefinition.model_validate(instance["data"]["definition"])
            if body.selected_option_id not in {o.option_id for o in definition.options}:
                raise APIError(422, "INVALID_OPTION", "Select an option issued with this quiz")
            correct = body.selected_option_id == definition.correct_option_id
            revision = conn.value(tables.users, "learning_revision", {"user_id": user_id}) + 1
            conn.update(tables.users, {"user_id": user_id}, {"learning_revision": revision})
            states = repo.learning_states(conn, user_id)
            for objective_id in definition.objective_ids:
                old = states.get(
                    objective_id,
                    {
                        "user_id": user_id,
                        "objective_id": objective_id,
                        "mastery_estimate": 0.5,
                        "correct_count": 0,
                        "incorrect_count": 0,
                        "misconception_tags": [],
                        "last_attempt_at": None,
                        "last_reviewed_at": None,
                        "next_review_at": None,
                        "revision": 0,
                    },
                )
                # Bounded, interpretable estimate. Viewing never enters this calculation.
                mastery = old["mastery_estimate"] * 0.65 + (0.35 if correct else 0)
                tags = set(old["misconception_tags"])
                misconception = definition.misconception_by_option.get(body.selected_option_id)
                if not correct and misconception:
                    tags.add(misconception)
                if correct:
                    tags.difference_update(definition.misconception_by_option.values())
                value = {
                    **old,
                    "mastery_estimate": mastery,
                    "correct_count": old["correct_count"] + int(correct),
                    "incorrect_count": old["incorrect_count"] + int(not correct),
                    "last_attempt_at": iso(now),
                    "last_reviewed_at": iso(now),
                    "next_review_at": iso(
                        now
                        + (
                            timedelta(days=1 if mastery < 0.8 else 3)
                            if correct
                            else timedelta(minutes=5)
                        )
                    ),
                    "misconception_tags": sorted(tags),
                    "revision": revision,
                }
                insert_ignore(
                    conn,
                    tables.learning,
                    {
                        "user_id": user_id,
                        "objective_id": objective_id,
                        "data": value,
                    },
                    ["user_id", "objective_id"],
                )
                conn.update(
                    tables.learning,
                    {"$and": [{"user_id": user_id}, {"objective_id": objective_id}]},
                    {"data": value},
                )
            state = self._unlock(conn, user_id, state, instance_id, "answered")
            attempt_id = new_id()
            response = {
                "schema_version": "1",
                "attempt_id": attempt_id,
                "accepted": True,
                "correct": correct,
                "explanation": definition.explanation,
                "scroll_unlocked": True,
                "learning_revision": revision,
                "recommendation_revision": state["recommendation_revision"],
            }
            conn.insert(
                tables.attempts,
                {
                    "attempt_id": attempt_id,
                    "instance_id": instance_id,
                    "user_id": user_id,
                    "data": {
                        "attempt_id": attempt_id,
                        "user_id": user_id,
                        "session_id": body.session_id,
                        "quiz_instance_id": instance_id,
                        "selected_option_id": body.selected_option_id,
                        "correct": correct,
                        "submitted_at": iso(now),
                        "objective_ids": definition.objective_ids,
                        "learning_revision": revision,
                        "response": response,
                    },
                },
            )
            publish(
                conn,
                event_type="learning.quiz.answered",
                user_id=user_id,
                aggregate_id=attempt_id,
                revision=revision,
                payload={
                    "attempt_id": attempt_id,
                    "objective_ids": definition.objective_ids,
                    "correct": correct,
                    "learning_revision": revision,
                },
                now=now,
            )
            if not correct:
                self._request_missing_variants(conn, user_id, instance, definition, revision, now)
            idempotency.remember(conn, user_id, route, key, request, response)
            return response

        return self.database.run(user_id, operation)

    def _request_missing_variants(self, conn, user_id, instance, definition, revision, now):
        # This is a reference-only handoff, never a call to a model or renderer.
        try:
            objectives = self.academics.list_objectives(user_id)
            variants = self.videos.list_variants(user_id, definition.objective_ids)
        except APIError as exc:
            if exc.status != 503:
                raise
            objectives, variants = [], []
        related = set(instance["data"]["related_video_ids"])
        related_approaches = {v.teaching_approach for v in variants if v.video_id in related}
        for objective_id in definition.objective_ids:
            objectives_for_id = [
                o for o in objectives if o.objective_id == objective_id and o.user_id == user_id
            ]
            has_alternative = any(
                v.video_id not in related
                and v.teaching_approach not in related_approaches
                and v.eligible(user_id, objective, now)
                for objective in objectives_for_id
                for v in variants
            )
            if not has_alternative:
                enqueue(
                    conn,
                    owner_user_id=user_id,
                    job_type="learning.reteach.requested",
                    dedupe_key=f"{objective_id}:{revision}",
                    input_ref={
                        "objective_id": objective_id,
                        "learning_revision": revision,
                        "quiz_instance_id": instance["instance_id"],
                    },
                    now=now,
                )

    def recover(self, user_id: str, instance_id: str, body: RecoveryRequest) -> dict:
        route = f"quizzes/{instance_id}/recover"
        request = body.model_dump(mode="json")

        def operation(conn):
            instance = self._instance(conn, user_id, instance_id, body.session_id)
            cached = idempotency.lookup(conn, user_id, route, body.client_event_id, request)
            if cached is not None:
                return cached
            state = repo.get_session(conn, user_id, body.session_id)
            if instance["state"] == "recovered":
                response = instance["data"]["recovery_response"]
            else:
                if (
                    instance["state"] != "pending"
                    or state["pending_quiz_instance_id"] != instance_id
                ):
                    raise APIError(409, "QUIZ_NOT_PENDING", "Only a pending quiz can be recovered")
                state = self._unlock(conn, user_id, state, instance_id, "recovered")
                response = {
                    "schema_version": "1",
                    "accepted": True,
                    "graded": False,
                    "scroll_unlocked": True,
                    "recommendation_revision": state["recommendation_revision"],
                }
                conn.update(
                    tables.quiz_instances,
                    {"$and": [{"instance_id": instance_id}, {"user_id": user_id}]},
                    {
                        "data": {
                            **instance["data"],
                            "recovery_response": response,
                            "recovery_reason": body.reason,
                            "recovered_at": iso(self.clock()),
                        }
                    },
                )
            idempotency.remember(conn, user_id, route, body.client_event_id, request, response)
            return response

        return self.database.run(user_id, operation)

    def progress(self, user_id: str) -> dict:
        objectives = [o for o in self.academics.list_objectives(user_id) if o.user_id == user_id]

        def operation(conn):
            states = repo.learning_states(conn, user_id)
            items = []
            for objective_id in sorted({o.objective_id for o in objectives}):
                state = states.get(objective_id)
                items.append(
                    {
                        "objective_id": objective_id,
                        "course_ids": sorted(
                            {o.course_id for o in objectives if o.objective_id == objective_id}
                        ),
                        "mastery_estimate": state["mastery_estimate"] if state else None,
                        "correct_count": state["correct_count"] if state else 0,
                        "incorrect_count": state["incorrect_count"] if state else 0,
                        "last_attempt_at": state["last_attempt_at"] if state else None,
                        "next_review_at": state["next_review_at"] if state else None,
                        "revision": state["revision"] if state else 0,
                    }
                )
            return {"schema_version": "1", "items": items, "next_cursor": None}

        return self.database.run(user_id, operation)
