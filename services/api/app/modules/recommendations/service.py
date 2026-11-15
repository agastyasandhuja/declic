from copy import deepcopy
from datetime import datetime

from app.core import collections as tables
from app.core import idempotency
from app.core.database import Database
from app.core.errors import APIError
from app.core.time import iso, new_id, parse_time, utc_now
from app.modules.quizzes.adapters import QuizReader
from app.modules.recommendations import repository as repo
from app.modules.recommendations.adapters import AcademicReader, EntertainmentReader, VideoReader
from app.modules.recommendations.engine import (
    DEFAULT_POLICY,
    Policy,
    select_study,
    slot,
    study_ratio,
)


class FeedService:
    def __init__(
        self,
        database: Database,
        academics: AcademicReader,
        entertainment: EntertainmentReader,
        videos: VideoReader,
        quizzes: QuizReader,
        *,
        clock=utc_now,
        policy: Policy = DEFAULT_POLICY,
    ):
        self.database = database
        self.academics = academics
        self.entertainment = entertainment
        self.videos = videos
        self.quizzes = quizzes
        self.clock = clock
        self.policy = policy

    def session_response(self, state: dict) -> dict:
        return {
            "schema_version": "1",
            **{
                key: state[key]
                for key in (
                    "session_id",
                    "started_at",
                    "last_active_at",
                    "recommendation_revision",
                    "pending_quiz_instance_id",
                )
            },
            "active_view_seconds": state["active_view_ms"] / 1000,
            "study_ratio_target": study_ratio(state["active_view_ms"] / 1000, self.policy),
        }

    def start_session(self, user_id: str, resume_session_id: str | None = None,
                      *, refresh_unseen=False, _connection=None) -> dict:
        now = self.clock()

        def operation(conn):
            if resume_session_id:
                state = repo.get_session(conn, user_id, resume_session_id)
            else:
                state = conn.value(
                    tables.sessions, "data", {"user_id": user_id}, sort=[("last_active", -1)]
                )
            # A pending/scheduled gate survives idle expiry and cannot be reset away.
            if state and (
                state["required_quiz_instance_id"]
                or (now - parse_time(state["last_active_at"])).total_seconds()
                <= self.database.settings.session_idle_seconds
            ):
                state["last_active_at"] = iso(now)
                repo.save_session(conn, user_id, state)
                if refresh_unseen and not state["required_quiz_instance_id"]:
                    state = repo.invalidate_user_feeds(conn, user_id)[state["session_id"]]
                    state["foreground"] = True
                    state["current_item_id"] = None
                    repo.save_session(conn, user_id, state)
            else:
                state = repo.create_session(conn, user_id, now)
            return self.session_response(state)

        if _connection is not None:
            return operation(_connection)
        return self.database.run(user_id, operation)

    def bootstrap(self, user_id: str, limit: int, preferred_video_ids: list[str], key: str) -> dict:
        """One authenticated transaction issues the startup page; hints are never authorization."""
        body = {"limit": limit, "preferred_video_ids": preferred_video_ids}

        def startup_page(conn, session_id):
            state = repo.get_session(conn, user_id, session_id)
            required = state["required_quiz_instance_id"]
            if required:
                gate = conn.value(tables.quiz_instances, "data", {
                    "user_id": user_id, "instance_id": required,
                })
                return {
                    "schema_version": "1", "session_id": session_id,
                    "recommendation_revision": state["recommendation_revision"],
                    "items": [gate["item"]], "next_cursor": None,
                    "pending_quiz_instance_id": state["pending_quiz_instance_id"],
                }
            return self.get_feed(
                user_id, session_id, None, limit,
                preferred_video_ids=preferred_video_ids, _connection=conn,
            )

        def operation(conn):
            prior = idempotency.lookup(conn, user_id, "feed/bootstrap", key, body)
            if prior:
                state = repo.get_session(conn, user_id, prior["session_id"])
                if state["recommendation_revision"] != prior["recommendation_revision"]:
                    raise APIError(409, "STALE_BOOTSTRAP", "Start a fresh feed request")
                # Refresh signed links and honor any gate activated since the retry.
                return startup_page(conn, state["session_id"])
            state = self.start_session(user_id, refresh_unseen=True, _connection=conn)
            page = startup_page(conn, state["session_id"])
            idempotency.remember(conn, user_id, "feed/bootstrap", key, body, {
                "session_id": page["session_id"],
                "recommendation_revision": page["recommendation_revision"],
            })
            return page

        return self.database.run(user_id, operation)

    def _issue(
        self,
        conn,
        user_id: str,
        state: dict,
        item: dict,
        now: datetime,
        history: dict | None = None,
    ) -> dict:
        state["sequence"] += 1
        item = {"item_id": new_id(), "inserted_at": iso(now), **item}
        data = {
            "item": item,
            "curriculum_revision": state.get("curriculum_revision", 0),
            "history": history,
            "watch_ms": 0,
            "reported_watch_ms": 0,
            "position_ms": 0,
            "exposed": False,
            "started": False,
            "terminal": False,
        }
        conn.insert(
            tables.occurrences,
            {
                "item_id": item["item_id"],
                "user_id": user_id,
                "session_id": state["session_id"],
                "revision": state["recommendation_revision"],
                "sequence": state["sequence"],
                "data": data,
            },
        )
        if history:
            state["history"] = [*state["history"], history][-50:]
        return item

    def _maybe_quiz(self, conn, user_id: str, state: dict, now: datetime) -> dict | None:
        exposures = state["quiz_exposures"]
        if len(exposures) < self.database.settings.quiz_after_study_exposures:
            return None
        exposed_objectives = {e["objective_id"] for e in exposures}
        authorized = {
            o.objective_id for o in self.academics.list_objectives(user_id) if o.user_id == user_id
        }
        for exposure in reversed(exposures):
            definitions = self.quizzes.list_for_objective(user_id, exposure["objective_id"])
            quiz_history = state.get("quiz_definition_history", [])
            for definition in sorted(
                definitions, key=lambda q: (quiz_history.count(q.quiz_id), q.quiz_id, -q.revision)
            ):
                if not set(definition.objective_ids).issubset(exposed_objectives & authorized) or (
                    definition.scope == "private" and definition.owner_user_id != user_id
                ):
                    continue
                instance_id = new_id()
                video_ids = list(
                    dict.fromkeys(
                        e["video_id"]
                        for e in exposures
                        if e["objective_id"] in definition.objective_ids
                    )
                )
                item = self._issue(
                    conn,
                    user_id,
                    state,
                    {
                        "kind": "quiz",
                        "reason_codes": ["review_due"],
                        "quiz": definition.card(instance_id, video_ids),
                    },
                    now,
                )
                conn.insert(
                    tables.quiz_instances,
                    {
                        "instance_id": instance_id,
                        "user_id": user_id,
                        "session_id": state["session_id"],
                        "item_id": item["item_id"],
                        "state": "issued",
                        "data": {
                            "definition": definition.model_dump(mode="json"),
                            "item": item,
                            "related_video_ids": video_ids,
                        },
                    },
                )
                state["quiz_definition_history"] = [*quiz_history, definition.quiz_id][-100:]
                state["required_quiz_instance_id"] = instance_id
                return item
        return None

    def _page(self, conn, user_id: str, state: dict, page_size: int) -> str:
        page_id = new_id()
        conn.insert(
            tables.pages,
            {
                "page_id": page_id,
                "user_id": user_id,
                "session_id": state["session_id"],
                "revision": state["recommendation_revision"],
                "page_size": page_size,
                "data": None,
            },
        )
        return page_id

    def _refresh_page(self, conn, user_id, state, page, now):
        """Revalidate cached pages: idempotency cannot preserve revoked/expired media."""
        response = deepcopy(page["data"])
        valid = []
        try:
            objectives = self.academics.list_objectives(user_id)
        except APIError as exc:
            if exc.status != 503:
                raise
            objectives = []
        try:
            clips = {c.video_id: c for c in self.entertainment.list_candidates(user_id, 200)}
        except APIError as exc:
            if exc.status != 503:
                raise
            clips = {}
        for item in response["items"]:
            if item["kind"] == "quiz":
                valid.append(item)
                continue
            available = False
            if item["kind"] == "entertainment_video":
                clip = clips.get(item["video"]["video_id"])
                if clip and clip.availability == "ready" and clip.playback.playable(now):
                    item["video"] = clip.model_dump(mode="json")
                    available = True
            else:
                try:
                    bound_lookup = getattr(self.videos, "get_variant_for_objective", None)
                    video = (bound_lookup(user_id, item["video"]["video_id"],
                                          item["course_context"]["objective_id"])
                             if bound_lookup else
                             self.videos.get_variant(user_id, item["video"]["video_id"]))
                    if video and video.playback and not video.playback.playable(now):
                        playback = self.videos.resolve_playback(user_id, video.video_id)
                        video = video.model_copy(update={"playback": playback})
                    if video and any(
                        o.course_id == item["course_context"]["course_id"]
                        and video.eligible(user_id, o, now)
                        for o in objectives
                    ):
                        item["video"] = video.public_summary()
                        available = True
                except APIError as exc:
                    if exc.status != 503:
                        raise
            occurrence = repo.get_occurrence(conn, user_id, state["session_id"], item["item_id"])
            occurrence["data"]["withdrawn"] = not available
            if available:
                occurrence["data"]["item"] = item
                valid.append(item)
            else:
                # Removed occurrences cannot be consumed, so they must stop
                # occupying the prefetch buffer. This grants no watch/exposure
                # credit, and their withdrawn flag still rejects late events.
                occurrence["data"]["terminal"] = True
            repo.save_occurrence(conn, occurrence)
        response["items"] = valid
        if len(valid) != len(page["data"]["items"]):
            response["availability"] = {
                "study": "ready"
                if any(i["kind"] == "study_video" for i in valid)
                else "unavailable",
                "entertainment": "ready"
                if any(i["kind"] == "entertainment_video" for i in valid)
                else "unavailable",
            }
        conn.update(
            tables.pages, {"page_id": page["page_id"], "user_id": user_id}, {"data": response}
        )
        return response

    def get_feed(self, user_id: str, session_id: str, cursor: str | None, limit: int,
                 *, preferred_video_ids: list[str] | None = None, _connection=None) -> dict:

        if not 1 <= limit <= self.database.settings.max_page_size:
            raise APIError(422, "INVALID_LIMIT", "Feed limit outside allowed range")
        now = self.clock()

        def operation(conn):
            state = repo.get_session(conn, user_id, session_id)
            page_id = cursor or state["root_page_id"]
            page = None
            if page_id:
                page = conn.find_one(
                    tables.pages,
                    {
                        "$and": [
                            {"page_id": page_id},
                            {"user_id": user_id},
                            {"session_id": session_id},
                        ]
                    },
                )
                if page is None:
                    raise APIError(404, "INVALID_CURSOR", "Feed cursor not found")
                if page["revision"] != state["recommendation_revision"]:
                    raise APIError(409, "STALE_CURSOR", "Fetch a new page without the old cursor")
                if page["page_size"] != limit:
                    raise APIError(
                        409, "CURSOR_QUERY_MISMATCH", "Keep the same page size for this cursor"
                    )
            if state["pending_quiz_instance_id"]:
                gate = conn.value(
                    tables.quiz_instances,
                    "data",
                    {
                        "$and": [
                            {"user_id": user_id},
                            {"instance_id": state["pending_quiz_instance_id"]},
                        ]
                    },
                )
                return {
                    "schema_version": "1",
                    "session_id": session_id,
                    "recommendation_revision": state["recommendation_revision"],
                    "items": [gate["item"]],
                    "next_cursor": None,
                    "pending_quiz_instance_id": state["pending_quiz_instance_id"],
                }
            if page is not None and page["data"] is not None and page["data"]["items"]:
                return self._refresh_page(conn, user_id, state, page, now)
            if state["required_quiz_instance_id"]:
                raise APIError(
                    409, "QUIZ_REQUIRED", "Resolve the issued quiz before requesting more items"
                )
            if not page_id:
                page_id = self._page(conn, user_id, state, limit)
                state["root_page_id"] = page_id
            try:
                quiz = self._maybe_quiz(conn, user_id, state, now)
            except APIError as exc:
                if exc.status != 503:
                    raise
                quiz = None
            items = [quiz] if quiz else []
            availability = {"study": "ready", "entertainment": "ready"}
            if not quiz:
                # Adapters are bounded cached reads; no provider retrieval or generation here.
                try:
                    objectives = [
                        o for o in self.academics.list_objectives(user_id) if o.user_id == user_id
                    ]
                    variants = self.videos.list_variants(
                        user_id, [o.objective_id for o in objectives]
                    )
                except APIError as exc:
                    if exc.status != 503:
                        raise
                    objectives, variants = [], []
                    availability["study"] = "unavailable"
                try:
                    clips = self.entertainment.list_candidates(user_id, 200)
                except APIError as exc:
                    if exc.status != 503:
                        raise
                    clips = []
                    availability["entertainment"] = "unavailable"
                # Provider duplicates cannot get extra ranking weight.
                clips = list(
                    {
                        (c.provider, c.provider_video_id): c
                        for c in clips
                        if c.availability == "ready" and c.playback.playable(now)
                    }.values()
                )
                states = repo.learning_states(conn, user_id)
                if not any(v.eligible(user_id, o, now) for o in objectives for v in variants):
                    availability["study"] = "unavailable"
                buffered = conn.count(
                    tables.occurrences,
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "revision": state["recommendation_revision"],
                        "data.terminal": False,
                    },
                )
                remaining = max(0, self.database.settings.max_unseen_slots - buffered)
                if not remaining:
                    raise APIError(
                        409, "FEED_BUFFER_FULL", "Consume the issued feed before prefetching more"
                    )
                startup_preference = (
                    list(dict.fromkeys(preferred_video_ids or [])) if cursor is None else []
                )
                for _ in range(min(limit, remaining)):
                    selection = select_study(
                        user_id=user_id,
                        objectives=objectives,
                        variants=variants,
                        learning=states,
                        history=state["history"],
                        now=now,
                        policy=self.policy,
                    )
                    study, debt = slot(
                        state["study_debt"],
                        state["active_view_ms"] / 1000,
                        selection is not None,
                        self.policy,
                    )
                    if not clips:
                        availability["entertainment"] = "unavailable"
                    if not clips and selection is not None and not study:
                        study = True
                        debt = max(0, debt - 1)
                    if study and selection:
                        objective, video = selection.objective, selection.variant
                        reason_text = "Reviewing " + objective.title + "."
                        if "quiz_weakness" in selection.reasons:
                            reason_text += " Practicing after a missed question."
                        if "upcoming_exam" in selection.reasons:
                            reason_text += " Relevant to a confirmed upcoming assessment."
                        item = {
                            "kind": "study_video",
                            "video": video.public_summary(),
                            "course_context": {
                                "course_id": objective.course_id,
                                "title": objective.course_title,
                                "objective_id": objective.objective_id,
                            },
                            "reason_text": reason_text,
                            "reason_codes": selection.reasons,
                            "constraint_relaxations": selection.relaxations,
                        }
                        if not clips:
                            item["reason_codes"] = [*item["reason_codes"], "inventory_fallback"]
                        history = {
                            "course_id": objective.course_id,
                            "objective_id": objective.objective_id,
                            "video_id": video.video_id,
                            "format_id": video.format_id,
                            "teaching_approach": video.teaching_approach,
                        }
                    elif clips:
                        # The study window is only 50 mixed slots. Using its counts
                        # for a 100-Reel catalog makes early IDs look unseen again
                        # before later clips are ever reached. Keep a separate,
                        # bounded least-recently-issued queue across page refreshes.
                        recent = state.get("entertainment_history")
                        if recent is None:
                            recent = list(dict.fromkeys(
                                h["video_id"] for h in state["history"] if "course_id" not in h
                            ))
                        positions = {video_id: index for index, video_id in enumerate(recent)}
                        last_id = state["history"][-1]["video_id"] if state["history"] else None
                        candidates = [c for c in clips if c.video_id != last_id]
                        if not candidates:
                            # Never immediately replay the only available clip.
                            break
                        cached = next((c for video_id in startup_preference
                                       for c in candidates if c.video_id == video_id), None)
                        clip = cached or min(
                            candidates, key=lambda c: (positions.get(c.video_id, -1), c.video_id)
                        )
                        # At most one slot gets a cache preference; the rest keep normal ranking.
                        startup_preference = []
                        state["entertainment_history"] = [
                            *[video_id for video_id in recent if video_id != clip.video_id],
                            clip.video_id,
                        ][-200:]
                        item = {
                            "kind": "entertainment_video",
                            "video": clip.model_dump(mode="json"),
                            "reason_codes": ["entertainment_slot"],
                        }
                        if selection is None:
                            item["reason_codes"].append("inventory_fallback")
                        history = {"video_id": clip.video_id}
                    else:
                        break
                    state["study_debt"] = debt
                    items.append(self._issue(conn, user_id, state, item, now, history))
            next_cursor = self._page(conn, user_id, state, limit) if items else None
            response = {
                "schema_version": "1",
                "session_id": session_id,
                "recommendation_revision": state["recommendation_revision"],
                "items": items,
                "next_cursor": next_cursor,
                "pending_quiz_instance_id": None,
                "availability": availability,
            }
            conn.update(
                tables.pages,
                {"$and": [{"page_id": page_id}, {"user_id": user_id}]},
                {"data": response},
            )
            state["last_active_at"] = iso(now)
            repo.save_session(conn, user_id, state)
            return response

        if _connection is not None:
            return operation(_connection)
        return self.database.run(user_id, operation)

    def activate_gate(self, user_id: str, session_id: str, instance_id: str, item_id: str) -> dict:

        def operation(conn):
            state = repo.get_session(conn, user_id, session_id)
            gate = conn.find_one(
                tables.quiz_instances,
                {
                    "$and": [
                        {"user_id": user_id},
                        {"session_id": session_id},
                        {"instance_id": instance_id},
                        {"item_id": item_id},
                    ]
                },
            )
            if gate is None:
                raise APIError(404, "NOT_FOUND", "Quiz instance not found")
            if gate["state"] not in {"answered", "recovered"}:
                if state["required_quiz_instance_id"] != instance_id:
                    raise APIError(409, "QUIZ_ORDER", "This is not the next required quiz")
                state["pending_quiz_instance_id"] = instance_id
                state["current_item_id"] = None
                state["last_active_at"] = iso(self.clock())
                conn.update(
                    tables.quiz_instances,
                    {"$and": [{"instance_id": instance_id}, {"user_id": user_id}]},
                    {"state": "pending"},
                )
                repo.save_session(conn, user_id, state)
            return {
                "schema_version": "1",
                "session_id": session_id,
                "pending_quiz_instance_id": state["pending_quiz_instance_id"],
                "scroll_locked": gate["state"] not in {"answered", "recovered"},
                "recommendation_revision": state["recommendation_revision"],
            }

        return self.database.run(user_id, operation)
