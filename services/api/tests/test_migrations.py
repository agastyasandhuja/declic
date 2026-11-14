import pytest
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.core.migrate import (
    MIGRATION_ID,
    VIDEO_MIGRATION_ID,
    apply_ordered,
    apply_video_indexes,
)


def require_mongo(database):
    if database.mongo is None:
        pytest.skip("Real MongoDB verification requires API_TEST_MONGODB_URI")
    return database.mongo


def test_ordered_setup_is_opt_in_repeatable_and_preserves_other_domains(database):
    db = require_mongo(database)
    db.academic_setup_sentinel.insert_one({"_id": "untouched", "revision": 7})
    apply_ordered(database)
    assert "video_generation_jobs" not in db.list_collection_names()
    assert db.api_migrations.find_one({"_id": VIDEO_MIGRATION_ID}) is None

    apply_ordered(database, include_videos=True)
    apply_ordered(database, include_videos=True)
    assert (
        db.api_migrations.count_documents({"_id": {"$in": [MIGRATION_ID, VIDEO_MIGRATION_ID]}}) == 2
    )
    assert db.academic_setup_sentinel.find_one({"_id": "untouched"}) == {
        "_id": "untouched",
        "revision": 7,
    }
    for collection, key, identity in (
        (db.video_generation_jobs, "generation_key", "job_id"),
        (db.video_variants, "generation_key", "video_id"),
        (db.video_outbox, "event_id", "event_id"),
    ):
        collection.insert_one({key: "duplicate", identity: "first"})
        with pytest.raises(DuplicateKeyError):
            collection.insert_one(
                {key: "duplicate", identity: "first" if key == identity else "second"}
            )


def test_failed_video_indexes_do_not_record_success_or_remove_conflicting_data(database):
    db = require_mongo(database)
    db.video_generation_jobs.insert_many(
        [
            {"job_id": "one", "generation_key": "duplicate"},
            {"job_id": "two", "generation_key": "duplicate"},
        ]
    )
    with pytest.raises(OperationFailure):
        apply_ordered(database, include_videos=True)
    assert db.api_migrations.find_one({"_id": VIDEO_MIGRATION_ID}) is None
    assert db.video_generation_jobs.count_documents({}) == 2
    # An operator resolves conflicting data explicitly; the migration never does.
    db.video_generation_jobs.delete_one({"job_id": "two"})
    apply_ordered(database, include_videos=True)
    assert db.api_migrations.find_one({"_id": VIDEO_MIGRATION_ID}) is not None


def test_video_migration_requires_api_predecessor(database):
    db = require_mongo(database)
    db.api_migrations.delete_one({"_id": MIGRATION_ID})
    with pytest.raises(ValueError, match="before video migration"):
        apply_video_indexes(database)
    assert "video_generation_jobs" not in db.list_collection_names()
