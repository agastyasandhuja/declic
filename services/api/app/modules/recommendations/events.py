from copy import deepcopy
from datetime import timedelta

from app.core import collections as tables
from app.core.database import Database
from app.core.errors import APIError
from app.core.idempotency import fingerprint
from app.core.time import iso, parse_time, utc_now
from app.modules.recommendations import repository as repo
from app.modules.recommendations.schemas import PlaybackEvent


class PlaybackEvents:
    def __init__(self, database: Database, clock=utc_now):
        self.database = database
        self.clock = clock

    def record(self, user_id: str, batch: list[PlaybackEvent]) -> dict:
        def operation(conn):
            accepted, rejected = [], []
            # All domain validation precedes writes. A database failure aborts/retries
            # the whole transaction; a rejected event does not mutate durable state.
            for event in batch:
                try:
                    self._record_one(conn, user_id, event)
                    accepted.append(event.event_id)
                except APIError as exc:
                    rejected.append({"event_id": event.event_id, "code": exc.code})
            return {"schema_version": "1", "accepted_event_ids": accepted, "rejected": rejected}

        return self.database.run(user_id, operation)

    def _record_one(self, conn, user_id: str, event: PlaybackEvent):
        now = self.clock()
        digest = fingerprint(event.model_dump(mode="json"))
        prior = conn.value(
            tables.events,
            "request_hash",
            {"$and": [{"user_id": user_id}, {"event_id": event.event_id}]},
        )
        if prior:
            if prior != digest:
                raise APIError(409, "EVENT_ID_CONFLICT", "Event ID identifies different data")
            return
        state = repo.get_session(conn, user_id, event.session_id)
        row = repo.get_occurrence(conn, user_id, event.session_id, event.item_id)
        data = deepcopy(row["data"])
        item = data["item"]
        if data.get("withdrawn"):
            raise APIError(409, "ITEM_UNAVAILABLE", "This feed item is no longer available")
        if item["kind"] == "quiz":
            raise APIError(422, "NOT_A_VIDEO", "Playback events require a video occurrence")
        if row["revision"] != state["recommendation_revision"] and not data["started"]:
            raise APIError(409, "STALE_ITEM", "Unseen item belongs to an old recommendation")
        at = event.client_occurred_at
        if at > now + timedelta(seconds=5) or at < now - timedelta(hours=24):
            raise APIError(422, "INVALID_EVENT_TIME", "Event timestamp outside allowed range")
        if at < parse_time(item["inserted_at"]) - timedelta(seconds=5):
            raise APIError(422, "INVALID_EVENT_TIME", "Event predates item issuance")
        if state["last_client_event_at"] and at < parse_time(state["last_client_event_at"]):
            raise APIError(409, "OUT_OF_ORDER_EVENT", "Retry events in chronological order")
        kind = event.event_type
        if state["pending_quiz_instance_id"] and kind not in {
            "app_backgrounded",
            "app_foregrounded",
        }:
            raise APIError(409, "QUIZ_REQUIRED", "Resolve the pending quiz first")
        payload = event.payload
        control_event = kind in {"app_backgrounded", "app_foregrounded"}
        duration = item["video"].get("duration_seconds")
        if not control_event and duration and payload.position_ms > duration * 1000 + 1000:
            raise APIError(422, "INVALID_PROGRESS", "Position exceeds video duration")
        looped = bool(duration and data["position_ms"] >= duration * 1000 - 4000
                      and payload.position_ms <= 4000
                      and payload.visible_watch_ms >= data["reported_watch_ms"])
        if not control_event and (
            payload.visible_watch_ms < data["reported_watch_ms"]
            or (payload.position_ms < data["position_ms"] and not looped)
        ):
            raise APIError(422, "NON_MONOTONIC_PROGRESS", "Playback progress must be monotonic")
        if kind == "app_foregrounded":
            state["foreground"] = True
            state["current_item_id"] = None  # Require a new playback anchor after backgrounding.
        elif kind == "app_backgrounded":
            state["foreground"] = False
            state["current_item_id"] = None
        elif kind == "playback_started":
            if not state["foreground"] or data["terminal"]:
                raise APIError(409, "PLAYBACK_INACTIVE", "Playback cannot start in this state")
            if payload.visible_watch_ms != data["reported_watch_ms"]:
                raise APIError(422, "INVALID_PROGRESS", "Start/resume cannot add watch time")
            state["current_item_id"] = event.item_id
            data.update(
                started=True,
                anchor_client=iso(at),
                anchor_server=iso(now),
                anchor_reported=payload.visible_watch_ms,
                anchor_credited=data["watch_ms"],
            )
        else:
            if (
                not state["foreground"]
                or state["current_item_id"] != event.item_id
                or data["terminal"]
            ):
                raise APIError(
                    409, "PLAYBACK_INACTIVE", "No active foreground playback for this item"
                )
            elapsed_ms = max(
                0,
                min(
                    (at - parse_time(data["anchor_client"])).total_seconds(),
                    (now - parse_time(data["anchor_server"])).total_seconds(),
                )
                * 1000,
            )
            reported = payload.visible_watch_ms - data["anchor_reported"]
            if reported > elapsed_ms + 250:
                raise APIError(422, "IMPLAUSIBLE_WATCH_TIME", "Watch time exceeds elapsed playback")
            total_credited = data["anchor_credited"] + min(reported, int(elapsed_ms))
            if duration:
                total_credited = min(total_credited, int(duration * 1000))
            added = max(0, total_credited - data["watch_ms"])
            data["watch_ms"] += added
            data["reported_watch_ms"] = payload.visible_watch_ms
            state["active_view_ms"] += added
            if kind in {"playback_completed", "video_skipped", "playback_failed"}:
                data["terminal"] = True
                state["current_item_id"] = None
            threshold = min(self.database.settings.exposure_seconds, (duration or 20) / 2) * 1000
            if not data["exposed"] and data["watch_ms"] >= threshold:
                data["exposed"] = True
                if item["kind"] == "study_video":
                    state["quiz_exposures"] = [
                        *state["quiz_exposures"],
                        {
                            "objective_id": item["course_context"]["objective_id"],
                            "video_id": item["video"]["video_id"],
                            "item_id": event.item_id,
                        },
                    ][-50:]
                # Watching counts as exposure only. It never changes mastery.
        if not control_event:
            data["position_ms"] = payload.position_ms
        row["data"] = data
        state["last_client_event_at"] = iso(at)
        state["last_active_at"] = iso(now)
        repo.save_occurrence(conn, row)
        repo.save_session(conn, user_id, state)
        conn.insert(
            tables.events,
            {
                "user_id": user_id,
                "event_id": event.event_id,
                "request_hash": digest,
                "received_at": now.timestamp(),
            },
        )
