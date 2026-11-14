"""Atlas academic store: owner scoping and revisions, against an in-memory fake
collection (no network). A live Atlas check runs only when MONGODB_TEST_URI is set."""

import os
import unittest
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from app.modules.curriculum import store
from app.modules.curriculum.atlas_store import AtlasAcademicStore


class FakeCollection:
    def __init__(self):
        self.docs = []

    def _match(self, doc, query):
        return all(doc.get(k) == v for k, v in query.items())

    def find_one(self, query, **kwargs):
        return next((dict(d) for d in self.docs if self._match(d, query)), None)

    def replace_one(self, query, doc, upsert=False, **kwargs):
        matched = sum(self._match(d, query) for d in self.docs)
        if matched or upsert:
            self.docs = [d for d in self.docs if not self._match(d, query)]
            self.docs.append(deepcopy(doc))
        return SimpleNamespace(matched_count=matched)

    def insert_one(self, doc, **kwargs):
        self.docs.append(deepcopy(doc))


class FakeDatabase(dict):
    @property
    def client(self):
        return self

    def start_session(self):
        return nullcontext(
            SimpleNamespace(with_transaction=lambda callback, **kwargs: callback(None))
        )

    def __missing__(self, name):
        self[name] = FakeCollection()
        return self[name]


def profile(user, rev):
    return {"user_id": user, "revision": rev, "courses": [{"course_id": "c1"}]}


class AtlasStoreTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDatabase()
        self.s = AtlasAcademicStore(self.db)

    def test_save_and_load_is_owner_scoped(self):
        self.s.save_profile("u1", profile("u1", 1))
        self.assertEqual(self.s.load_profile("u1")["revision"], 1)
        self.assertIsNone(self.s.load_profile("u2"))  # another user sees nothing

    def test_refuses_foreign_owner(self):
        with self.assertRaises(PermissionError):
            self.s.save_profile("u1", profile("u2", 1))
        with self.assertRaises(PermissionError):
            self.s.save_plans("u1", [{"user_id": "u2"}])

    def test_revisions_kept_and_current_updated(self):
        self.s.save_profile("u1", profile("u1", 1))
        self.s.save_profile("u1", profile("u1", 2))
        self.assertEqual(self.s.latest_revision("u1"), 2)
        self.assertEqual(len(self.db["academic_profile_revisions"].docs), 2)
        self.assertEqual(len(self.db["academic_profiles"].docs), 1)

    def test_plans_round_trip(self):
        self.s.save_plans("u1", [{"user_id": "u1", "plan_id": "p1"}])
        self.assertEqual(self.s.load_plans("u1"), [{"user_id": "u1", "plan_id": "p1"}])
        self.assertEqual(self.s.load_plans("u2"), [])

    def test_store_module_routes_to_atlas_when_enabled(self):
        store.use_atlas(self.db)
        self.addCleanup(store.use_atlas, None)
        store.save_profile(Path("/nonexistent"), "u1", profile("u1", 1))
        self.assertEqual(store.load_profile(Path("/nonexistent"), "u1")["revision"], 1)


@unittest.skipUnless(os.environ.get("MONGODB_TEST_URI"), "set MONGODB_TEST_URI for a live check")
class LiveAtlasTests(unittest.TestCase):
    def test_live_round_trip_and_cleanup(self):
        from pymongo import MongoClient

        client = MongoClient(os.environ["MONGODB_TEST_URI"], serverSelectionTimeoutMS=10000)
        self.addCleanup(client.close)
        db = client[os.environ.get("MONGODB_DATABASE", "hackumass")]
        user = "synthetic-test-user-academics"
        self.addCleanup(
            lambda: [
                db[c].delete_many({"user_id": user})
                for c in (
                    "academic_profiles",
                    "academic_profile_revisions",
                    "academic_lesson_plans",
                )
            ]
        )
        s = AtlasAcademicStore(db)
        s.save_profile(user, profile(user, 1))
        s.save_plans(user, [{"user_id": user, "plan_id": "p"}])
        self.assertEqual(s.load_profile(user)["revision"], 1)
        self.assertEqual(len(s.load_plans(user)), 1)


if __name__ == "__main__":
    unittest.main()
