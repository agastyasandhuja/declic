"""API-owned collections; never initialize producer-owned collections here."""

users = "api_user_state"
sessions = "api_feed_sessions"
occurrences = "api_feed_occurrences"
pages = "api_feed_pages"
events = "api_feed_events"
quiz_instances = "api_quiz_instances"
attempts = "api_quiz_attempts"
learning = "api_topic_learning_state"
idempotency = "api_idempotency"
jobs = "api_jobs"
outbox = "api_outbox"
processed = "api_processed_events"
connections = "api_provider_connections"
topics = "api_prepared_topics"
bindings = "api_topic_bindings"
quiz_bank = "api_quiz_bank"

KEYS = {
    connections: ("user_id", "provider"),
    topics: ("user_id", "topic_id"),
    bindings: ("user_id", "objective_id"),
    quiz_bank: ("user_id", "quiz_id"),
    users: ("user_id",),
    sessions: ("session_id",),
    occurrences: ("item_id",),
    pages: ("page_id",),
    events: ("user_id", "event_id"),
    quiz_instances: ("instance_id",),
    attempts: ("attempt_id",),
    learning: ("user_id", "objective_id"),
    idempotency: ("user_id", "route", "key"),
    jobs: ("job_id",),
    outbox: ("event_id",),
    processed: ("consumer", "event_id"),
}
UNIQUE = {
    occurrences: [("session_id", "sequence")],
    attempts: [("instance_id",)],
    jobs: [("owner_user_id", "job_type", "dedupe_key")],
}
INDEXES = {
    sessions: [("user_id", "last_active")],
    occurrences: [("user_id", "session_id", "sequence")],
    pages: [("user_id", "session_id", "revision")],
    quiz_instances: [("user_id", "session_id", "state")],
    attempts: [("user_id",)],
    learning: [("user_id",)],
    jobs: [("job_type", "state", "available_at"), ("state", "lease_until")],
    outbox: [("event_type", "created_at")],
}
