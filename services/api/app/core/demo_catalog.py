"""Explicit generic demo catalog and owner-scoped learning mode; no generation here."""

import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core import collections as tables
from app.core.dependencies import CurrentUser
from app.core.request_cache import cached, invalidate
from app.modules.quizzes.schemas import QuizDefinition
from app.modules.recommendations import repository as feed_repo
from app.modules.recommendations.models import Identifier, ObjectiveCandidate
from app.modules.videos.adapters import FeedVideoReader

CATALOG_ID = "shared_demo_v1"
CATALOG_OWNER = "system_shared_demo"
COURSES = {"demo_cs210", "demo_acc233", "demo_his110", "demo_math235"}
SUPPLEMENTAL_COURSE = "demo_cs220"
PRESENTATION_OBJECTIVES = frozenset(
    {
        "demo_cs210_stack_undo",
        "demo_cs220_promise_states",
        "demo_acc233_perpetual",
        "demo_his110_wright_1903",
    }
)


def minimum_demo_duration(format_id):
    return 20 if format_id == "math_explainer" else 30


class DemoModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DemoCourse(DemoModel):
    course_id: Identifier
    title: str = Field(min_length=1, max_length=200)


class DemoObjective(DemoModel):
    objective_id: Identifier
    course_id: Identifier
    title: str = Field(min_length=1, max_length=200)
    level: Literal["intro"] = "intro"
    language: Literal["en"] = "en"
    notation: Literal["general"] = "general"


class DemoQuiz(QuizDefinition):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DemoLesson(DemoModel):
    objective_id: Identifier
    video_id: Identifier
    quizzes: list[DemoQuiz] = Field(min_length=2, max_length=4)


class DemoManifest(DemoModel):
    schema_version: Literal["1"] = "1"
    catalog_id: Literal["shared_demo_v1"] = CATALOG_ID
    revision: int = Field(strict=True, ge=1)
    courses: list[DemoCourse] = Field(min_length=4, max_length=5)
    objectives: list[DemoObjective] = Field(min_length=4, max_length=25)
    lessons: list[DemoLesson] = Field(min_length=24, max_length=25)

    @model_validator(mode="after")
    def generic_only(self):
        course_ids = {c.course_id for c in self.courses}
        if len(course_ids) != len(self.courses) or not COURSES <= course_ids <= (
            COURSES | {SUPPLEMENTAL_COURSE}
        ):
            raise ValueError("Use the four core demo courses and optional CS 220")
        objectives = {o.objective_id: o for o in self.objectives}
        if len(objectives) != len(self.objectives):
            raise ValueError("Duplicate objective")
        if any(
            not o.objective_id.startswith("demo_") or o.course_id not in course_ids
            for o in self.objectives
        ):
            raise ValueError("Demo objectives must use a separate generic namespace")
        if len({v.video_id for v in self.lessons}) != len(self.lessons):
            raise ValueError("Publish distinct reviewed videos")
        quiz_ids = [quiz.quiz_id for lesson in self.lessons for quiz in lesson.quizzes]
        if len(set(quiz_ids)) != len(quiz_ids):
            raise ValueError("Demo quiz IDs must be unique")
        expected_counts = dict.fromkeys(COURSES, 6)
        if SUPPLEMENTAL_COURSE in course_ids:
            expected_counts[SUPPLEMENTAL_COURSE] = 1
        counts = dict.fromkeys(course_ids, 0)
        for lesson in self.lessons:
            if lesson.objective_id not in objectives:
                raise ValueError("Lesson must bind a declared objective")
            for quiz in lesson.quizzes:
                if quiz.objective_ids != [lesson.objective_id]:
                    raise ValueError("Quiz must bind its lesson objective")
                if (
                    quiz.scope != "shared_generic"
                    or quiz.owner_user_id is not None
                    or quiz.source_refs
                    or not quiz.quiz_id.startswith("demo_")
                ):
                    raise ValueError("Private quizzes and source references cannot enter the demo")
            counts[objectives[lesson.objective_id].course_id] += 1
        if counts != expected_counts:
            raise ValueError("Publish six lessons per core course and one for optional CS 220")
        return self


class DemoCatalog:
    def __init__(self, database, video_service, *, objective_ids=None):
        self.objective_ids = objective_ids
        self.database = database
        self.video_service = video_service
        self.video_reader = FeedVideoReader(video_service)

    def manifest(self):
        return cached((id(self), "manifest"), self._manifest)

    def _manifest(self):
        row = self.database.read(
            lambda tx: tx.find_one(
                tables.demo_catalogs, {"catalog_id": CATALOG_ID, "user_id": CATALOG_OWNER}
            )
        )
        if not row:
            return None
        manifest = DemoManifest.model_validate(row["data"])
        if self.objective_ids is None:
            return manifest
        lessons = [
            lesson for lesson in manifest.lessons if lesson.objective_id in self.objective_ids
        ]
        active_ids = {lesson.objective_id for lesson in lessons}
        objectives = [o for o in manifest.objectives if o.objective_id in active_ids]
        course_ids = {o.course_id for o in objectives}
        # Project the reviewed registry; the archived library stays intact.
        return manifest.model_copy(
            update={
                "lessons": lessons,
                "objectives": objectives,
                "courses": [c for c in manifest.courses if c.course_id in course_ids],
            }
        )

    def publish(self, manifest):
        """Operator-only registration after trusted generic asset publication."""
        manifest = DemoManifest.model_validate(manifest)
        objectives = {o.objective_id: o for o in manifest.objectives}
        for lesson in manifest.lessons:
            # This fixed, non-student actor can only find shared generic assets.
            video = self.video_service.repository.video(lesson.video_id, CATALOG_OWNER)
            objective = objectives[lesson.objective_id]
            if (
                not video
                or video.get("scope") != "shared_generic"
                or video.get("owner_user_id") is not None
                or video.get("status") != "ready"
                or video.get("objective_id") != lesson.objective_id
                or (video.get("level"), video.get("language"), video.get("notation"))
                != (objective.level, objective.language, objective.notation)
                or not minimum_demo_duration(video.get("format_id"))
                <= video.get("duration_seconds", 0)
                <= 60
            ):
                raise ValueError("Demo requires ready generic assets with matching objectives")
            quality = video.get("quality_checks", {})
            if quality.get("media_checks") != "passed" or quality.get("publication_policy") not in {
                "human_reviewed_v1",
                "agent_reviewed_generic_demo_v1",
            }:
                raise ValueError("Demo asset review is missing")
        data = manifest.model_dump(mode="json")

        def save(tx):
            query = {"catalog_id": CATALOG_ID, "user_id": CATALOG_OWNER}
            old = tx.find_one(tables.demo_catalogs, query)
            if old and old["data"] == data:
                return
            if manifest.revision != ((old or {}).get("data", {}).get("revision", 0) + 1):
                raise ValueError("Demo catalog revision must advance by one")
            tx.insert_if_absent(tables.demo_catalogs, {**query, "data": data}, ["catalog_id"])
            tx.update(tables.demo_catalogs, query, {"data": data})

        self.database.run(CATALOG_OWNER, save)
        invalidate()
        return self.public()

    def public(self):
        manifest = self.manifest()
        if manifest is None:
            return {"schema_version": "1", "revision": 0, "courses": []}
        return {
            "schema_version": "1",
            "revision": manifest.revision,
            "courses": [
                {
                    **course.model_dump(),
                    "objectives": [
                        {"objective_id": o.objective_id, "title": o.title}
                        for o in manifest.objectives
                        if o.course_id == course.course_id
                    ],
                    "video_count": sum(
                        1
                        for lesson in manifest.lessons
                        if next(
                            o for o in manifest.objectives if o.objective_id == lesson.objective_id
                        ).course_id
                        == course.course_id
                    ),
                }
                for course in manifest.courses
            ],
        }

    def list_objectives(self, user_id):
        manifest = self.manifest()
        if not manifest:
            return []
        titles = {c.course_id: c.title for c in manifest.courses}
        return [
            ObjectiveCandidate(
                **o.model_dump(),
                user_id=user_id,
                course_title=titles[o.course_id],
            )
            for o in manifest.objectives
        ]

    def list_variants(self, user_id, objective_ids):
        return cached(
            (id(self), user_id, "variants", tuple(objective_ids)),
            lambda: self._list_variants(user_id, objective_ids),
        )

    def _list_variants(self, user_id, objective_ids):
        manifest = self.manifest()
        if not manifest:
            return []
        allowed = {
            lesson.video_id for lesson in manifest.lessons if lesson.objective_id in objective_ids
        }
        # Never use personalized topic bindings, even when this owner has them.
        videos = [
            v
            for v in self.video_service.repository.list_videos(user_id, objective_ids)
            if v["video_id"] in allowed
            and v.get("scope") == "shared_generic"
            and v.get("owner_user_id") is None
            and v.get("status") == "ready"
        ]
        signed = self.video_reader._sign_owned(videos) if videos else {}
        return [self.video_reader._project(user_id, v, signed) for v in videos]

    def get_variant(self, user_id, video_id):
        manifest = self.manifest()
        objective = (
            next((v.objective_id for v in manifest.lessons if v.video_id == video_id), None)
            if manifest
            else None
        )
        return (
            next(
                (v for v in self.list_variants(user_id, [objective]) if v.video_id == video_id),
                None,
            )
            if objective
            else None
        )

    def get_variant_for_objective(self, user_id, video_id, objective_id):
        video = self.get_variant(user_id, video_id)
        return video if video and video.objective_id == objective_id else None

    def resolve_playback(self, user_id, video_id):
        video = self.get_variant(user_id, video_id)
        return video.playback if video else None

    def list_for_objective(self, user_id, objective_id):
        manifest = self.manifest()
        return (
            [
                quiz
                for lesson in manifest.lessons
                if lesson.objective_id == objective_id
                for quiz in lesson.quizzes
            ]
            if manifest
            else []
        )


class LearningSettings:
    def __init__(self, database):
        self.database = database

    def enabled(self, user_id):
        return cached((id(self), user_id, "demo_mode"), lambda: self._enabled(user_id))

    def _enabled(self, user_id):
        row = self.database.read(lambda tx: tx.find_one(tables.users, {"user_id": user_id}))
        return (row or {}).get("demo_mode", False) is True

    def update(self, user_id, enabled):
        def save(tx):
            row = tx.find_one(tables.users, {"user_id": user_id})
            if row.get("demo_mode", False) is enabled:
                return {
                    "schema_version": "1",
                    "demo_mode": enabled,
                    "recommendation_revision": None,
                }
            tx.update(tables.users, {"user_id": user_id}, {"demo_mode": enabled})
            # Generation fence rejects even previously-started cards without
            # rewriting the entire historical occurrence collection.
            states = [row["data"] for row in tx.find(tables.sessions, {"user_id": user_id})]
            for state in states:
                if enabled:
                    state["demo_feed_policy"] = feed_repo.DEMO_FEED_POLICY
                feed_repo.reset_curriculum(tx, user_id, state, "curriculum_mode_changed")
            return {
                "schema_version": "1",
                "demo_mode": enabled,
                "recommendation_revision": max(
                    (s["recommendation_revision"] for s in states), default=None
                ),
            }

        result = self.database.run(user_id, save)
        invalidate()
        return result


class ModeReader:
    """Select complete provider boundaries using the authenticated owner's setting."""

    def __init__(self, settings, demo, personalized):
        self.settings, self.demo, self.personalized = settings, demo, personalized

    def __getattr__(self, name):
        if name not in {
            "list_objectives",
            "list_variants",
            "get_variant",
            "get_variant_for_objective",
            "resolve_playback",
            "list_for_objective",
        }:
            raise AttributeError(name)

        def call(user_id, *args):
            source = self.demo if self.settings.enabled(user_id) else self.personalized
            method = getattr(source, name, None)
            if method is None and name == "get_variant_for_objective":
                return source.get_variant(user_id, args[0])
            return method(user_id, *args)

        return call


class SettingsUpdate(DemoModel):
    demo_mode: bool = Field(strict=True)


def create_router(settings, catalog):
    router = APIRouter(prefix="/v1/learning", tags=["learning settings"])

    @router.get("/settings")
    def get(user: CurrentUser):
        return {"schema_version": "1", "demo_mode": settings.enabled(user.user_id)}

    @router.patch("/settings")
    def patch(body: SettingsUpdate, user: CurrentUser):
        return settings.update(user.user_id, body.demo_mode)

    @router.get("/demo-catalog")
    def demo_catalog(user: CurrentUser):
        return catalog.public()

    return router


if __name__ == "__main__":
    import argparse

    from app.full_runtime import components

    parser = argparse.ArgumentParser(
        description="Register an explicitly reviewed generic demo catalog"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", required=True)
    args = parser.parse_args()
    database, _, _, video_service, _ = components()
    try:
        result = DemoCatalog(database, video_service).publish(json.loads(args.manifest.read_text()))
        print(json.dumps({"revision": result["revision"], "courses": len(result["courses"])}))
    finally:
        database.close()
