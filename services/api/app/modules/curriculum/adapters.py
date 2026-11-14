"""Projection for Agastya's AcademicReader interface."""
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.modules.recommendations.models import ObjectiveCandidate


class FeedAcademicReader:
    def __init__(self, service):
        self.service = service

    def list_objectives(self, user_id: str) -> list[ObjectiveCandidate]:
        profile = self.service.get_profile(user_id)
        if profile is None:
            return []
        courses = {course["course_id"]: course for course in profile["courses"]}
        assessments = {item["assessment_id"]: item for item in profile["assessments"]}
        candidates = []
        for plan in self.service.get_validated_plans(user_id):
            if plan["profile_revision"] != profile["revision"]:
                continue
            course = courses[plan["course_id"]]
            for request in plan["requests"]:
                linked = [assessments[key] for key in request["assessment_ids"]
                          if key in assessments and assessments[key]["course_id"] == course["course_id"]]
                assessment = min(linked, key=lambda item: item["scheduled"].get("date") or "9999", default={})
                scheduled = assessment.get("scheduled", {})
                zone = scheduled.get("timezone") or course.get("timezone") or "UTC"
                try:
                    ZoneInfo(zone)
                except (ValueError, ZoneInfoNotFoundError):
                    zone = "UTC"
                candidates.append(ObjectiveCandidate(
                    user_id=user_id, course_id=course["course_id"],
                    course_title=course.get("title") or "Course",
                    objective_id=request["objective_id"], title=request["title"],
                    level="intro", language="en", notation="general",
                    prerequisite_objective_ids=request["prerequisite_objective_ids"],
                    assessment_scope_status=assessment.get("scope_status", "unknown"),
                    assessment_evidence_status=scheduled.get("evidence_status", "unknown"),
                    assessment_date=scheduled.get("date"),
                    assessment_timestamp=scheduled.get("timestamp"), timezone=zone,
                ))
        return candidates
