"""Durable academic-to-lesson handoff. No model or renderer work on feed requests."""

from itertools import zip_longest

from app.core import collections as tables
from app.core.time import iso, utc_now
from app.modules.canvas.client.http import CanvasAuthError
from app.modules.curriculum.source_quality import (
    InsufficientTeachingEvidence,
    teaching_sources,
    validate_teaching_lesson,
)
from app.modules.curriculum.sources import CanvasSourceResolver
from app.modules.quizzes.generation import prepare_lesson
from app.modules.quizzes.schemas import QuizDefinition
from app.modules.videos.models import Brief, digest
from app.modules.videos.pipeline import generation_recipe
from app.workers.queue import enqueue


class SupersededPreparation(Exception):
    """The lesson request changed while model work was in flight."""


class LearningPipeline:
    def __init__(self, database, connections, academics, client, topics, video_repository):
        self.database, self.connections, self.academics = database, connections, academics
        self.client, self.topics, self.videos = client, topics, video_repository

    def _guard_connection(self, tx, context):
        # Real connections validate in the same transaction as publication. Fake
        # adapters retain their small documented client interface in unit tests.
        guard = getattr(self.connections, "require_current", None)
        if guard is not None:
            guard(context.owner_user_id, context.input_ref["connection_id"], tx)

    def _request(self, context):
        return next(
            (
                request
                for plan in self.academics.get_validated_plans(context.owner_user_id)
                if plan["profile_revision"] == context.input_ref["profile_revision"]
                for request in plan["requests"]
                if request["lesson_request_id"] == context.input_ref["lesson_request_id"]
            ),
            None,
        )

    def sync(self, context):
        owner, connection_id = context.owner_user_id, context.input_ref["connection_id"]
        client = self.connections.client(owner, connection_id)

        def authorized():
            row = self.connections.get(owner)
            return bool(
                context.heartbeat()
                and row
                and row["status"] == "connected"
                and row["connection_id"] == connection_id
            )

        try:
            profile = self.academics.import_profile(
                owner,
                CanvasSourceResolver(client, owner_user_id=owner),
                publication_guard=authorized,
            )
        except CanvasAuthError:
            self.database.run(
                owner,
                lambda tx: tx.update(
                    tables.connections,
                    {"user_id": owner, "provider": "canvas", "connection_id": connection_id},
                    {"status": "reconnect_required"},
                ),
            )
            raise
        plans = self.academics.get_validated_plans(owner)
        # Round robin ensures every course gets its first lesson before the next
        # course's second lesson, independent of inventory size.
        ordered = [
            item
            for row in zip_longest(*(plan["requests"] for plan in plans))
            for item in row
            if item is not None
        ]

        def publish(tx):
            self._guard_connection(tx, context)
            for request in ordered:
                enqueue(
                    tx,
                    owner_user_id=owner,
                    job_type="learning.prepare",
                    dedupe_key=f"{profile['revision']}:{request['lesson_request_id']}",
                    input_ref={
                        "lesson_request_id": request["lesson_request_id"],
                        "profile_revision": profile["revision"],
                        "connection_id": connection_id,
                    },
                )
            tx.update(
                tables.connections,
                {"user_id": owner, "provider": "canvas", "connection_id": connection_id},
                {"last_sync_at": iso(utc_now())},
            )

        if not authorized():
            raise PermissionError("Import no longer authorized")
        self.database.run(owner, publish)
        return {
            "profile_id": profile["profile_id"],
            "revision": profile["revision"],
            "courses": [
                {"course_id": course["course_id"], "import_status": course["import_status"]}
                for course in profile["courses"]
            ],
            "queued_lessons": len(ordered),
        }

    def prepare(self, context):
        owner = context.owner_user_id
        self.connections.client(owner, context.input_ref["connection_id"])
        request = self._request(context)
        if request is None:
            return {"state": "superseded"}
        sources = self.academics.resolve_source_context(owner, request["source_refs"])
        if not teaching_sources(sources):
            return self._unavailable(context, request["objective_id"])
        ready = self.database.read(
            lambda tx: tx.find_one(
                tables.quiz_bank,
                {
                    "user_id": owner,
                    "objective_id": request["objective_id"],
                    "profile_revision": context.input_ref["profile_revision"],
                    "active": True,
                },
            )
        )
        binding = self.database.read(
            lambda tx: tx.find_one(
                tables.bindings,
                {
                    "user_id": owner,
                    "objective_id": request["objective_id"],
                    "profile_revision": context.input_ref["profile_revision"],
                },
            )
        )
        if ready and binding:
            topic = self.database.read(
                lambda tx: tx.find_one(
                    tables.topics, {"user_id": owner, "topic_id": binding["topic_id"]}
                )
            )
            try:
                validate_teaching_lesson((topic or {}).get("lesson", {}))
            except InsufficientTeachingEvidence:
                return self._unavailable(context, request["objective_id"])
            return {"topic_id": binding["topic_id"], "reused": True}
        try:
            lesson = prepare_lesson(self.client, request, sources)
        except InsufficientTeachingEvidence:
            return self._unavailable(context, request["objective_id"])
        self.connections.client(owner, context.input_ref["connection_id"])
        canonical = lesson.model_dump()
        definition = QuizDefinition(
            quiz_id="quiz_" + digest([owner, request["objective_id"], canonical])[:32],
            revision=1,
            objective_ids=[request["objective_id"]],
            prompt=canonical["prompt"],
            options=[
                {"option_id": str(i), "text": option}
                for i, option in enumerate(canonical["options"])
            ],
            correct_option_id=str(canonical["correct_index"]),
            explanation=canonical["explanation"],
            scope="private",
            owner_user_id=owner,
            source_refs=[
                {"source_id": ref} if isinstance(ref, str) else ref
                for ref in request["source_refs"]
            ],
        )

        def save(tx, topic, reused):
            self._guard_connection(tx, context)
            if self._request(context) != request:
                raise SupersededPreparation()
            tx.update(
                tables.quiz_bank,
                {"user_id": owner, "objective_id": request["objective_id"]},
                {"active": False},
            )
            tx.insert_if_absent(
                tables.quiz_bank,
                {
                    "user_id": owner,
                    "quiz_id": definition.quiz_id,
                    "objective_id": request["objective_id"],
                    "definition": definition.model_dump(mode="json"),
                    "profile_revision": context.input_ref["profile_revision"],
                },
                ["user_id", "quiz_id"],
            )
            tx.update(
                tables.quiz_bank,
                {"user_id": owner, "quiz_id": definition.quiz_id},
                {"active": True, "profile_revision": context.input_ref["profile_revision"]},
            )
            tx.update(
                tables.bindings,
                {"user_id": owner, "objective_id": request["objective_id"]},
                {"profile_revision": context.input_ref["profile_revision"]},
            )
            enqueue(
                tx,
                owner_user_id=owner,
                job_type="learning.render",
                dedupe_key=topic["topic_id"],
                input_ref={"topic_id": topic["topic_id"]},
            )

        if not context.heartbeat():
            raise RuntimeError("Lease lost")
        try:
            topic, reused = self.topics.bind(
                owner, request["objective_id"], lesson.model_dump(), on_bind=save
            )
        except SupersededPreparation:
            return {"state": "superseded"}
        return {"topic_id": topic["topic_id"], "reused": reused}

    def _unavailable(self, context, objective_id):
        def revoke(tx):
            self._guard_connection(tx, context)
            tx.update(
                tables.quiz_bank,
                {
                    "user_id": context.owner_user_id,
                    "objective_id": objective_id,
                    "profile_revision": context.input_ref["profile_revision"],
                },
                {"active": False},
            )

        self.database.run(context.owner_user_id, revoke)
        return {"state": "unavailable", "reason": "INSUFFICIENT_TEACHING_EVIDENCE"}

    def reteach(self, context):
        # The alternate visual/dialogue pair shares a canonical topic, never a
        # foreign user's lesson. Repeated requests reuse the same generation keys.
        binding = self.database.read(
            lambda tx: tx.find_one(
                tables.bindings,
                {
                    "user_id": context.owner_user_id,
                    "objective_id": context.input_ref["objective_id"],
                },
            )
        )
        if not binding:
            return {"state": "topic_unavailable"}
        from app.workers.runner import JobContext

        return self.render(
            JobContext(
                context.job_id,
                context.owner_user_id,
                {"topic_id": binding["topic_id"]},
                context.heartbeat,
            ),
            retry_failed=True,
        )

    def render(self, context, *, retry_failed=False):
        owner = context.owner_user_id
        topic = self.database.read(
            lambda tx: tx.find_one(
                tables.topics, {"user_id": owner, "topic_id": context.input_ref["topic_id"]}
            ),
        )
        if not topic:
            raise LookupError("Topic unavailable")
        lesson, topic_id = topic["lesson"], topic["topic_id"]
        try:
            validate_teaching_lesson(lesson)
            sources = self.academics.resolve_source_context(owner, lesson.get("source_ids", []))
            if not teaching_sources(sources):
                raise InsufficientTeachingEvidence("Teaching sources unavailable")
        except (InsufficientTeachingEvidence, LookupError):
            return {"state": "unavailable", "reason": "INSUFFICIENT_TEACHING_EVIDENCE"}
        facts = [{"fact_id": f"f{i}", "statement": fact} for i, fact in enumerate(lesson["facts"])]
        recipe = generation_recipe()
        jobs = []
        for format_id, approach in [
            ("visual_explainer", "visual_story"),
            ("dialogue_gameplay", "conversation"),
        ]:
            brief = Brief(
                brief_id=topic_id + "_" + approach,
                lesson_request_id=topic_id,
                objective_id=topic_id,
                title=lesson["title"],
                learning_goal=lesson["learning_goal"],
                subject=lesson["subject"],
                level=topic["compatibility"]["level"],
                notation="general",
                assumed_knowledge=[],
                must_cover=[fact["fact_id"] for fact in facts],
                must_not_claim=["Do not claim confirmed exam coverage."],
                approved_facts=facts,
                trace_kind="none",
                format_id=format_id,
                visual_strategy="semantic_diagram"
                if format_id == "visual_explainer"
                else "existing",
                teaching_approach=approach,
                scope="private",
                owner_user_id=owner,
            )
            job = self.videos.enqueue(
                brief.generation_key(recipe), owner, brief.model_dump(), recipe
            )
            if retry_failed and job["state"] == "failed":
                self.videos.retry_failed(job["job_id"], owner)
            jobs.append(job["job_id"])
        return {"video_job_ids": jobs}


class StoredQuizzes:
    def __init__(self, database):
        self.database = database

    def list_for_objective(self, user_id, objective_id):
        rows = self.database.read(
            lambda tx: tx.find(
                tables.quiz_bank,
                {"user_id": user_id, "objective_id": objective_id, "active": True},
                limit=10,
            )
        )
        if self.database.mongo is not None:
            profile = self.database.mongo.academic_profiles.find_one(
                {"user_id": user_id}, {"revision": 1}
            )
            if profile is not None:
                rows = [row for row in rows if row.get("profile_revision") == profile["revision"]]
        return [QuizDefinition.model_validate(row["definition"]) for row in rows]
