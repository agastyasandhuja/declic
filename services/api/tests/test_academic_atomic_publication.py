from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier

import pytest

from app.modules.curriculum.atlas_store import AtlasAcademicStore, apply_academic_drafts
from app.modules.curriculum.corrections import RevisionConflict


@pytest.fixture
def atlas(database):
    if database.mongo is None:
        pytest.skip("Requires disposable API_TEST_MONGODB_URI")
    apply_academic_drafts(database.mongo)
    return AtlasAcademicStore(database.mongo)


def profile(owner, revision, label):
    return {
        "user_id": owner,
        "revision": revision,
        "courses": [{"course_id": label}],
        "_sources": [{"source_id": label, "course_id": label, "text": label}],
        "_plans": [{"user_id": owner, "profile_revision": revision, "course_id": label}],
    }


@pytest.mark.parametrize("initial_revision", [0, 1])
def test_concurrent_imports_commit_one_immutable_profile_snapshot(
    atlas, database, initial_revision
):
    if initial_revision:
        atlas.save_profile("alice", profile("alice", 1, "old"))
    barrier = Barrier(2)

    def publish(label):
        snapshot = profile("alice", initial_revision + 1, label)
        barrier.wait()
        try:
            AtlasAcademicStore(database.mongo).save_profile("alice", snapshot)
            return snapshot
        except RevisionConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(publish, ["course-a", "course-b"]))
    winners = [item for item in results if item is not None]
    assert len(winners) == 1
    assert atlas.load_profile("alice") == winners[0]
    assert (
        database.mongo.academic_profile_revisions.count_documents({"user_id": "alice"})
        == initial_revision + 1
    )
    archived = database.mongo.academic_profile_revisions.find_one(
        {"user_id": "alice", "revision": initial_revision + 1}
    )
    assert archived["profile"] == winners[0]
    atlas.save_profile("alice", deepcopy(winners[0]))  # Safe ambiguous-commit retry.
    assert atlas.load_profile("bob") is None


def test_rejected_archive_write_rolls_back_current_profile(atlas, database):
    original = profile("alice", 1, "original")
    atlas.save_profile("alice", original)
    archive = database.mongo.academic_profile_revisions.find_one(
        {"user_id": "alice", "revision": 1}
    )
    archive.pop("_id")
    archive.update(revision=2, profile=profile("alice", 2, "preexisting-immutable"))
    database.mongo.academic_profile_revisions.insert_one(archive)
    with pytest.raises(RevisionConflict):
        atlas.save_profile("alice", profile("alice", 2, "new"))
    assert atlas.load_profile("alice") == original
    assert (
        database.mongo.academic_profile_revisions.find_one({"user_id": "alice", "revision": 2})[
            "profile"
        ]
        == archive["profile"]
    )


def test_guard_and_stale_correction_cannot_publish(atlas, database):
    atlas.save_profile("alice", profile("alice", 1, "original"))
    with pytest.raises(PermissionError):
        atlas.save_profile("alice", profile("alice", 2, "revoked"), publication_guard=lambda: False)
    assert atlas.latest_revision("alice") == 1
    atlas.save_profile("alice", profile("alice", 2, "corrected"))
    with pytest.raises(RevisionConflict):
        atlas.save_profile("alice", profile("alice", 2, "old-import"))
    assert atlas.load_profile("alice")["courses"][0]["course_id"] == "corrected"
    assert database.mongo.academic_profile_revisions.count_documents({"user_id": "alice"}) == 2
