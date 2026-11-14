"""Standalone Atlas connectivity checks; never a replacement shared DB client.

Default mode is read-only. --write-test commits/rolls back synthetic records only
in a fresh _adi_atlas_probe_<random> collection, then drops that exact collection.
Credentials are read locally and never included in output or reports.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4
import warnings

from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError, ServerSelectionTimeoutError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

ROOT = Path(__file__).resolve().parents[5]


class ConfigurationError(ValueError):
    pass


def load_configuration(env_file: Path | None, environ=None, allow_local=False):
    values = {}
    if env_file:
        for line in env_file.read_text().splitlines():
            key, separator, value = line.partition('=')
            key = key.strip().removeprefix('export ')
            if separator and key in {'MONGODB_URI', 'MONGODB_DATABASE', 'API_MONGODB_URI', 'API_MONGODB_DATABASE'}:
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('\"', "'"):
                    value = value[1:-1]
                values[key] = value
    values.update(os.environ if environ is None else environ)
    uri = values.get('MONGODB_URI') or values.get('API_MONGODB_URI') or ''
    name = values.get('MONGODB_DATABASE') or values.get('API_MONGODB_DATABASE') or 'hackumass'
    if not uri:
        raise ConfigurationError('Set MONGODB_URI in a local server environment file.')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,63}', name) or name in {'admin', 'local', 'config'}:
        raise ConfigurationError('Choose an application database name.')
    try:
        url = urlsplit(uri)
        _ = url.port  # reject malformed authorities without exposing their text
        if url.fragment or url.path not in ('', '/', '/' + name):
            raise ValueError()
        local = allow_local and url.scheme == 'mongodb' and url.hostname in {'127.0.0.1', 'localhost', '::1'}
        if not local and (url.scheme != 'mongodb+srv' or not url.hostname or not url.hostname.endswith('.mongodb.net')):
            raise ValueError()
        options = [(key.lower(), value.lower()) for key, value in parse_qsl(url.query)]
        if any((key in {'tls', 'ssl'} and value == 'false') or (key in {'tlsinsecure', 'tlsallowinvalidcertificates', 'tlsallowinvalidhostnames'} and value != 'false') for key, value in options):
            raise ValueError()
    except ValueError:
        raise ConfigurationError('Use an Atlas SRV URI with verified TLS and a matching database path. Local URIs require the explicit test flag.') from None
    return uri, name, bool(local)


def owned_schema_checks(database):
    results = {}
    for domain in ('identity', 'entertainment'):
        manifest = json.loads((ROOT / f'database/domains/{domain}/manifest.json').read_text())
        for spec in manifest['collections']:
            options = list(database.list_collections(filter={'name': spec['name']}))
            validator_ok = (bool(options) and options[0]['options'].get('validator') == spec['validator']
                            and options[0]['options'].get('validationLevel', 'strict') == 'strict'
                            and options[0]['options'].get('validationAction', 'error') == 'error')
            indexes = database[spec['name']].index_information() if options else {}
            indexes_ok = all(
                index['name'] in indexes and list(indexes[index['name']]['key']) == [tuple(key) for key in index['keys']]
                and all(indexes[index['name']].get(key) == value for key, value in index.items() if key not in {'name', 'keys'})
                for index in spec['indexes']
            )
            results[spec['name']] = {'present': bool(options), 'validator_matches': validator_ok, 'indexes_match': indexes_ok}
    return results


class IntentionalRollback(Exception):
    pass


def transaction_probe(client, database, report):
    name = '_adi_atlas_probe_' + uuid4().hex
    report['probe_collection'] = name  # nonsecret identifier for cleanup if interrupted
    report['probe_cleanup'] = False
    created = False
    try:
        collection = database.create_collection(name)
        created = True
        with client.start_session() as session:
            options = {'read_concern': ReadConcern('snapshot'), 'write_concern': WriteConcern('majority', wtimeout=5000), 'max_commit_time_ms': 5000}
            with session.start_transaction(**options):
                collection.insert_many([{'_id': 1, 'value': 0}, {'_id': 2, 'value': 0}], session=session)
            if collection.count_documents({}) != 2:
                raise RuntimeError('Synthetic commit failed')
            report['transaction_commit_verified'] = True
            try:
                with session.start_transaction(**options):
                    collection.update_one({'_id': 1}, {'$set': {'value': 1}}, session=session)
                    raise IntentionalRollback()
            except IntentionalRollback:
                pass
            if collection.find_one({'_id': 1})['value'] != 0:
                raise RuntimeError('Synthetic rollback failed')
            report['transaction_rollback_verified'] = True
    finally:
        if created:
            database.drop_collection(name)
            report['probe_cleanup'] = True
            report.pop('probe_collection', None)


def preflight(uri, database_name, *, local=False, write_test=False, apply_owned_drafts=False):
    report = {'schema_version': '1', 'checked_at': datetime.now(timezone.utc).isoformat(),
              'target': 'local_test' if local else 'atlas', 'database': database_name,
              'connection_verified': False, 'transaction_commit_verified': False,
              'transaction_rollback_verified': False, 'write_test_requested': write_test,
              'owned_draft_apply_requested': apply_owned_drafts}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            client = MongoClient(uri, appname='hackumass-adi-atlas-preflight', serverSelectionTimeoutMS=5000,
                                 connectTimeoutMS=5000, timeoutMS=10000, tz_aware=True)
        with client:
            client.admin.command('ping')
            report['connection_verified'] = True
            hello = client.admin.command('hello')
            report['replica_set_detected'] = bool(hello.get('setName'))
            report['logical_sessions_detected'] = hello.get('logicalSessionTimeoutMinutes') is not None
            database = client[database_name]
            if apply_owned_drafts:
                from .database_setup import apply_domain_drafts
                apply_domain_drafts(database)
                report['owned_drafts_applied'] = True
            report['adi_schema_checks'] = owned_schema_checks(database)
            report['core_migrations'] = {identifier: database.api_migrations.find_one({'_id': identifier}, {'_id': 1}) is not None
                                         for identifier in ('001_api_learning_runtime', '002_video_indexes')}
            if write_test:
                transaction_probe(client, database, report)
        report['status'] = 'completed'
    except ServerSelectionTimeoutError:
        report.update(status='failed', error_code='CONNECTION_UNAVAILABLE')
    except OperationFailure as error:
        report.update(status='failed', error_code={18: 'AUTH_FAILED', 13: 'ACCESS_DENIED'}.get(error.code, 'DATABASE_OPERATION_FAILED'))
    except (PyMongoError, ValueError, TypeError):
        report.update(status='failed', error_code='DATABASE_CONFIGURATION_OR_OPERATION_FAILED')
    except Exception:
        report.update(status='failed', error_code='PREFLIGHT_FAILED')
    return report


def write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(report, stream, indent=2)
        stream.write('\n')
    temporary.chmod(0o600)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, help='Read MongoDB variables only; process environment takes priority.')
    parser.add_argument('--write-test', action='store_true', help='Create/commit/rollback/drop one fresh synthetic probe collection.')
    parser.add_argument('--apply-owned-drafts', action='store_true', help='Apply only Adi identity/entertainment drafts; refuse conflicting validators.')
    parser.add_argument('--allow-local-for-test', action='store_true')
    parser.add_argument('--report', type=Path, default=ROOT / '.local/atlas-readiness/report.json')
    args = parser.parse_args()
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)  # standalone CLI: raw driver diagnostics stay private
    try:
        try:
            uri, name, local = load_configuration(args.env_file, allow_local=args.allow_local_for_test)
        except (ConfigurationError, OSError, UnicodeError):
            print('Atlas configuration is missing or invalid. Check the local server env file; no connection attempted.')
            return 2
        report = preflight(uri, name, local=local, write_test=args.write_test, apply_owned_drafts=args.apply_owned_drafts)
        try:
            write_report(args.report, report)
        except OSError:
            print('Could not save the local preflight report. Check the destination permissions.')
            return 1
        print(json.dumps(report, indent=2))
        return 0 if report['status'] == 'completed' else 1
    finally:
        logging.disable(previous_logging)


if __name__ == '__main__':
    raise SystemExit(main())
