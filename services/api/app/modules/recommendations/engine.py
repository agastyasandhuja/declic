"""Deterministic, database/provider-independent recommendation policy."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.time import parse_time
from app.modules.recommendations.models import ObjectiveCandidate, VariantCandidate


@dataclass(frozen=True)
class Policy:
    ramp: tuple[tuple[int, float], ...] = ((0, 0.10), (120, 0.20), (300, 0.35), (600, 0.50))
    exam_weight: float = 0.30
    weakness_weight: float = 0.25
    current_weight: float = 0.20
    review_weight: float = 0.15
    novelty_weight: float = 0.10
    max_course_run: int = 2
    course_window: int = 10
    max_course_in_window: int = 4
    max_study_debt: float = 1.0
    recent_objective_penalty: float = 0.15


DEFAULT_POLICY = Policy()


def study_ratio(active_seconds: float, policy: Policy = DEFAULT_POLICY) -> float:
    return next(ratio for start, ratio in reversed(policy.ramp) if active_seconds >= start)


def slot(
    debt: float, active_seconds: float, study_available: bool, policy: Policy = DEFAULT_POLICY
) -> tuple[bool, float]:
    if study_available and debt >= policy.max_study_debt:
        return True, max(0, debt - 1)
    # Preserve the fractional remainder while inventory exists (e.g. 35%, not 33%).
    debt += study_ratio(active_seconds, policy)
    if study_available and debt >= 1 - 1e-9:
        return True, max(0, debt - 1)
    # Preserve at most one owed lesson when inventory is absent.
    return False, min(policy.max_study_debt, debt)


def exam_urgency(objective: ObjectiveCandidate, now: datetime) -> float:
    confirmed = {"explicit", "user_confirmed"}
    if (
        objective.assessment_scope_status not in confirmed
        or objective.assessment_evidence_status not in confirmed
    ):
        return 0
    if objective.assessment_timestamp is not None:
        days = (objective.assessment_timestamp - now).total_seconds() / 86400
    elif objective.assessment_date is not None:
        # Preserve date-only precision in the course's timezone; never invent midnight.
        days = (
            objective.assessment_date - now.astimezone(ZoneInfo(objective.timezone)).date()
        ).days
    else:
        return 0
    return max(0, 1 - days / 14) if days >= 0 else 0


def objective_score(
    objective: ObjectiveCandidate, state: dict | None, now: datetime, seen: set[str], policy: Policy
) -> tuple[float, list[str]]:
    urgency = exam_urgency(objective, now)
    weakness = 0 if not state else 1 - state["mastery_estimate"]
    review_due = bool(
        state and state.get("next_review_at") and parse_time(state["next_review_at"]) <= now
    )
    novelty = 0 if objective.objective_id in seen else 1
    reasons = []
    if urgency:
        reasons.append("upcoming_exam")
    if state and state["incorrect_count"] and weakness > 0.4:
        reasons.append("quiz_weakness")
    if objective.current_unit:
        reasons.append("current_unit")
    if review_due:
        reasons.append("review_due")
    score = (
        policy.exam_weight * urgency
        + policy.weakness_weight * weakness
        + policy.current_weight * objective.current_unit
        + policy.review_weight * review_due
        + policy.novelty_weight * novelty
    )
    return score, reasons


@dataclass(frozen=True)
class Selection:
    objective: ObjectiveCandidate
    variant: VariantCandidate
    reasons: list[str]
    relaxations: list[str]
    score: float


def select_study(
    *,
    user_id: str,
    objectives: list[ObjectiveCandidate],
    variants: list[VariantCandidate],
    learning: dict[str, dict],
    history: list[dict],
    now: datetime,
    policy: Policy = DEFAULT_POLICY,
) -> Selection | None:
    """History includes issued reservations AND consumed exposures for spacing.

    Fairness counts study slots only. Video/objective cooldown looks at the last
    video slot, so intervening entertainment can make reteaching eligible.
    """
    study_history = [h for h in history if h.get("course_id")]
    recent = study_history[-policy.course_window :]
    recent_courses = Counter(h["course_id"] for h in recent)
    total_courses = Counter(h["course_id"] for h in study_history)
    seen = {h["objective_id"] for h in study_history}
    last_video = history[-1] if history else {}
    by_objective: dict[str, list[VariantCandidate]] = defaultdict(list)
    for variant in variants:
        by_objective[variant.objective_id].append(variant)
    courses: dict[str, list[tuple]] = defaultdict(list)
    for objective in objectives:
        if objective.user_id != user_id or objective.objective_id == last_video.get("objective_id"):
            continue
        available = [
            v
            for v in by_objective[objective.objective_id]
            if v.eligible(user_id, objective, now) and v.video_id != last_video.get("video_id")
        ]
        if not available:
            continue
        state = learning.get(objective.objective_id)
        # Known weak prerequisites defer advanced lessons, unknown ones stay neutral.
        if any(
            learning.get(p, {}).get("mastery_estimate", 0.5) < 0.4
            for p in objective.prerequisite_objective_ids
        ):
            continue
        score, reasons = objective_score(objective, state, now, seen, policy)
        recent_index = next(
            (
                i
                for i, h in enumerate(reversed(study_history))
                if h["objective_id"] == objective.objective_id
            ),
            None,
        )
        if recent_index is not None:
            score -= policy.recent_objective_penalty / (recent_index + 1)
        if any(
            s.get("incorrect_count", 0) >= 2
            and objective.objective_id in o.prerequisite_objective_ids
            for o in objectives
            for s in [learning.get(o.objective_id, {})]
        ):
            score += 0.35
            reasons.append("prerequisite_review")
        last_variant = next(
            (h for h in reversed(study_history) if h["objective_id"] == objective.objective_id), {}
        )
        video_counts = Counter(h["video_id"] for h in study_history)
        # A new teaching approach and format win before a previously used variant.
        available.sort(
            key=lambda v: (
                v.video_id == last_variant.get("video_id"),
                v.teaching_approach == last_variant.get("teaching_approach"),
                v.format_id == last_variant.get("format_id"),
                video_counts[v.video_id],
                v.video_id,
            )
        )
        chosen = available[0]
        if last_variant and chosen.teaching_approach != last_variant.get("teaching_approach"):
            reasons.append("new_explanation")
        courses[objective.course_id].append((score, objective, chosen, reasons))
    if not courses:
        return None
    eligible = list(courses)
    relaxations = []
    if len(eligible) >= 3:
        capped = [c for c in eligible if recent_courses[c] < policy.max_course_in_window]
        if capped:
            eligible = capped
        else:
            relaxations.append("course_window_limit")
    run = study_history[-policy.max_course_run :]
    if len(run) == policy.max_course_run and len({h["course_id"] for h in run}) == 1:
        alternate = [c for c in eligible if c != run[-1]["course_id"]]
        if alternate:
            eligible = alternate
        else:
            relaxations.append("course_run_limit")
    # Course coverage is primary, objective scores break course ties. Inventory
    # size never contributes: 20/4/2 variants cannot buy disproportionate exposure.
    chosen_course = min(
        eligible,
        key=lambda c: (
            total_courses[c],
            -max(item[0] for item in courses[c]),
            c,
        ),
    )
    score, objective, variant, reasons = min(
        courses[chosen_course], key=lambda x: (-x[0], x[1].objective_id)
    )
    return Selection(objective, variant, [*reasons, "course_diversity"], relaxations, score)
