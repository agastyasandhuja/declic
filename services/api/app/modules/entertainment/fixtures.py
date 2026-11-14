"""Explicit synthetic adapter for local API development; no social login required."""
import json

from .service import ROOT, normalized_items


class FixtureCatalog:
    def __init__(self):
        self.items = normalized_items(json.loads((ROOT / 'fixtures/entertainment/feed.json').read_text())['items'])

    def read_items(self, user):
        # Public test media, deliberately identical for all authenticated test users.
        return self.items
