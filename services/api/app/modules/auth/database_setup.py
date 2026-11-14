"""Adi-owned draft installer. Agastya assembles these into ordered migrations."""
import argparse
import json
import os
from pathlib import Path

from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[5]


def apply_domain_drafts(database):
    for domain in ('identity', 'entertainment'):
        manifest = json.loads((ROOT / f'database/domains/{domain}/manifest.json').read_text())
        for spec in manifest['collections']:
            existing = list(database.list_collections(filter={'name': spec['name']}))
            if not existing:
                database.create_collection(spec['name'], validator=spec['validator'], validationLevel='strict', validationAction='error')
            elif (existing[0]['options'].get('validator') != spec['validator']
                  or existing[0]['options'].get('validationLevel', 'strict') != 'strict'
                  or existing[0]['options'].get('validationAction', 'error') != 'error'):
                raise RuntimeError(f"{spec['name']}: existing validator differs; integrator must plan a backfill/migration.")
            collection = database[spec['name']]
            for index in spec['indexes']:
                collection.create_index([tuple(key) for key in index['keys']], **{k: v for k, v in index.items() if k != 'keys'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Apply additive owned drafts to configured database; never drops data/indexes.')
    args = parser.parse_args()
    if not args.apply:
        parser.error('Explicit --apply required. Configure server-only MONGODB_URI and MONGODB_DATABASE.')
    name = os.environ['MONGODB_DATABASE']
    if name in ('admin', 'local', 'config') or not name:
        raise SystemExit('Choose an application database.')
    with MongoClient(os.environ['MONGODB_URI'], serverSelectionTimeoutMS=5000, timeoutMS=10000) as client:
        apply_domain_drafts(client[name])
    print('Identity and entertainment drafts applied; no private seed data imported.')
