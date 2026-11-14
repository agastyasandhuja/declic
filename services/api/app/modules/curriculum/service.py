"""Owner-scoped academic services backed by a private local snapshot."""

from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .corrections import RevisionConflict, correct_profile, restore_corrections
from .extract import build_profile
from .handoff import build_profile_ready_event
from .planning.planner import build_lesson_plans, is_source_backed_practice
from .store import LOCK, latest_revision, load_plans, load_profile, save_profile
from .timing import priority_targets, target_topic_is_supported


class AcademicService:
    def __init__(self, storage_dir: Path, client, *, clock=lambda: datetime.now(UTC)):
        self.storage_dir = storage_dir
        self.client = client
        self.clock = clock

    def get_profile(self, user_id):
        profile = load_profile(self.storage_dir, user_id, include_sources=False)
        if profile is None:
            return None
        return {key: value for key, value in profile.items() if not key.startswith("_")}

    def get_validated_plans(self, user_id):
        profile = load_profile(self.storage_dir, user_id, include_sources=False)
        return self._validated_plans(user_id, profile)

    def get_feed_snapshot(self, user_id):
        """Project profile and plans from the same revision with one private read."""
        profile = load_profile(self.storage_dir, user_id, include_sources=False)
        if profile is None:
            return None, []
        public = {key: value for key, value in profile.items() if not key.startswith("_")}
        return public, self._validated_plans(user_id, profile)

    def _validated_plans(self, user_id, profile):
        if profile is None:
            return []
        plans = profile.get("_plans")
        if plans is None:
            plans = load_plans(self.storage_dir, user_id)
        courses = {course["course_id"]: course for course in profile["courses"]}
        valid = []
        for plan in plans:
            if (
                plan.get("user_id") != user_id
                or plan.get("profile_id") != profile["profile_id"]
                or plan.get("profile_revision") != profile["revision"]
                or plan.get("status") != "validated"
                or plan.get("course_id") not in courses
            ):
                continue
            plan = deepcopy(plan)
            course = courses[plan["course_id"]]
            if course.get("external_course_id"):
                targets = priority_targets(
                    [
                        item
                        for item in profile["assessments"]
                        if item["course_id"] == course["course_id"]
                    ],
                    self.clock(),
                    course.get("timezone"),
                )
                retained = []
                for request in plan["requests"]:
                    topic = request.get("timeline_topic")
                    matches = [
                        item
                        for item in targets
                        if item["assessment_id"] in request["assessment_ids"]
                        and isinstance(topic, str)
                        and target_topic_is_supported(topic, item)
                    ]
                    if is_source_backed_practice(
                        request,
                        course,
                        profile.get("units", []),
                        [
                            a
                            for a in profile["assessments"]
                            if a["course_id"] == course["course_id"]
                        ],
                        self.clock(),
                    ):
                        retained.append(request)
                    elif matches:
                        request["assessment_ids"] = [item["assessment_id"] for item in matches]
                        exam = next(
                            (
                                item
                                for item in matches
                                if item["kind"] in {"midterm", "final"} or item.get("is_exam")
                            ),
                            None,
                        )
                        request["exam_scope_status"] = exam["scope_status"] if exam else "unknown"
                        retained.append(request)
                plan["requests"] = retained
            if plan["requests"]:
                valid.append(plan)
        return valid

    def get_course_bindings(self, user_id):
        profile = self.get_profile(user_id)
        if profile is None:
            return []
        return [
            {
                "binding_id": request["binding_id"],
                "user_id": user_id,
                "course_id": plan["course_id"],
                "objective_id": request["objective_id"],
                "unit_id": request.get("unit_id"),
                "coverage_status": request["evidence_status"],
                "assessment_ids": request["assessment_ids"],
                "source_refs": request["source_refs"],
            }
            for plan in self.get_validated_plans(user_id)
            for request in plan["requests"]
        ]

    def resolve_source_context(self, user_id, source_refs):
        profile = load_profile(self.storage_dir, user_id) or {}
        sources = {source["source_id"]: source for source in profile.get("_sources", [])}
        result = []
        for ref in source_refs:
            source_id = ref.get("source_id") if isinstance(ref, dict) else ref
            source = sources.get(source_id) if isinstance(source_id, str) else None
            if source is None or (
                isinstance(ref, dict) and ref.get("course_id") != source["course_id"]
            ):
                raise LookupError("source unavailable")
            result.append(dict(source))
        return result

    def apply_corrections(self, user_id, revision, changes):
        with LOCK:
            profile = load_profile(self.storage_dir, user_id)
            if profile is None:
                raise LookupError("profile unavailable")
            correct_profile(profile, revision, changes)
            # Previous lesson requests are superseded until planned against these corrections.
            profile["_plans"] = []
            profile["_ready_event"] = None
            save_profile(self.storage_dir, user_id, profile)
            return self.get_profile(user_id)

    def import_profile(self, user_id, resolver, *, publication_guard=None):
        profile = build_profile(user_id, resolver, self.client, self.storage_dir, persist=False)
        if all(course["import_status"] == "error" for course in profile["courses"]):
            raise ValueError("no course extraction succeeded")
        if hasattr(resolver, "assignments_for_course"):
            from .run_demo import _attach_timing

            _attach_timing(profile, resolver)
        plans = build_lesson_plans(profile, self.client, resolver)
        with LOCK:
            if publication_guard is not None and not publication_guard():
                raise PermissionError("import no longer authorized")
            current = latest_revision(self.storage_dir, user_id)
            if profile["revision"] != current + 1:
                raise RevisionConflict("profile changed during import; retry")
            restore_corrections(self.storage_dir, user_id, profile)
            profile["_sources"] = [asdict(source) for source in resolver.list_sources()]
            profile["_plans"] = plans
            validated = [
                plan for plan in plans if plan["status"] == "validated" and plan["requests"]
            ]
            profile["lesson_plan_ids"] = [plan["plan_id"] for plan in validated]
            profile["binding_ids"] = [
                request["binding_id"] for plan in validated for request in plan["requests"]
            ]
            profile["_ready_event"] = (
                build_profile_ready_event(profile, validated) if validated else None
            )
            save_profile(self.storage_dir, user_id, profile, publication_guard=publication_guard)
        return self.get_profile(user_id)
