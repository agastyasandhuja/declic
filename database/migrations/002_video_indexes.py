"""Run after 001 using python -m app.core.migrate --apply --include-videos.

Delegates to the video owner's public initializer; no copied schema definitions.
Does not publish media, process jobs, or consume the video outbox.
"""

from app.core.migrate import apply_video_indexes


def upgrade(database):
    apply_video_indexes(database)
