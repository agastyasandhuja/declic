"""Projection for Agastya's AcademicReader interface."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.modules.recommendations.models import ObjectiveCandidate

from .planning.planner import is_source_backed_practice
from .timing import priority_targets, target_topic_is_supported, upcoming_assessments


class FeedAcademicReader:
    def __init__(self, service, *, clock=lambda: datetime.now(UTC)):
        self.service = service
        self.clock = clock

    def list_objectives(self, user_id: str) -> list[ObjectiveCandidate]:
        profile = self.service.get_profile(user_id)
        if profile is None:
            return []
        courses = {course["course_id"]: course for course in profile["courses"]}
        assessments = {item["assessment_id"]: item for item in profile["assessments"]}
        candidates = []
        now = self.clock()
        for plan in self.service.get_validated_plans(user_id):
            if plan["profile_revision"] != profile["revision"]:
                continue
            course = courses[plan["course_id"]]
            course_assessments = [
                item for item in assessments.values() if item["course_id"] == course["course_id"]
            ]
            targets = priority_targets(course_assessments, now, course.get("timezone"))
            for request in plan["requests"]:
                linked = [
                    assessments[key]
                    for key in request["assessment_ids"]
                    if key in assessments and assessments[key]["course_id"] == course["course_id"]
                ]
                if course.get("external_course_id"):
                    topic = request.get("timeline_topic")
                    linked = [
                        item
                        for item in targets
                        if item["assessment_id"] in request["assessment_ids"]
                        and isinstance(topic, str)
                        and target_topic_is_supported(topic, item)
                    ]
                    if not linked and not is_source_backed_practice(
                        request, course, profile.get("units", []), course_assessments, now
                    ):
                        continue
                else:
                    linked = upcoming_assessments(linked, now, course.get("timezone"))
                assessment = linked[0] if linked else {}
                scheduled = assessment.get("scheduled", {})
                zone = scheduled.get("timezone") or course.get("timezone") or "UTC"
                try:
                    ZoneInfo(zone)
                except (ValueError, ZoneInfoNotFoundError):
                    zone = "UTC"
                candidates.append(
                    ObjectiveCandidate(
                        user_id=user_id,
                        course_id=course["course_id"],
                        course_title=course.get("title") or "Course",
                        objective_id=request["objective_id"],
                        title=request["title"],
                        level="intro",
                        language="en",
                        notation="general",
                        prerequisite_objective_ids=request["prerequisite_objective_ids"],
                        current_unit=bool(linked),
                        assessment_scope_status=request["exam_scope_status"]
                        if linked
                        else "unknown",
                        assessment_evidence_status=scheduled.get("evidence_status", "unknown"),
                        assessment_date=scheduled.get("date"),
                        assessment_timestamp=scheduled.get("timestamp"),
                        timezone=zone,
                    )
                )
        return candidates
