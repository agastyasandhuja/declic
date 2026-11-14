import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from app.modules.auth import atlas_preflight as check
from app.modules.auth.database_setup import apply_domain_drafts


class ConfigurationTests(unittest.TestCase):
    def test_cloud_config_is_tls_verified_and_local_override_is_explicit(self):
        uri = 'mongodb+srv://synthetic:PRIVATE@cluster.example.mongodb.net/?retryWrites=true&w=majority'
        self.assertEqual(check.load_configuration(None, {'MONGODB_URI': uri})[1:], ('hackumass', False))
        for invalid in (uri + '&tls=false', uri + '&tlsInsecure=true', uri + '&tlsAllowInvalidCertificates=true', uri.replace('cluster.example.mongodb.net', 'outside.example.test'), 'mongodb://127.0.0.1:27028'):
            with self.assertRaises(check.ConfigurationError):
                check.load_configuration(None, {'MONGODB_URI': invalid})
        self.assertTrue(check.load_configuration(None, {'MONGODB_URI': 'mongodb://127.0.0.1:27028'}, allow_local=True)[2])
        with self.assertRaises(check.ConfigurationError):
            check.load_configuration(None, {'MONGODB_URI': uri, 'MONGODB_DATABASE': 'admin'})

    def test_only_mongodb_env_values_are_loaded_and_process_values_win(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('MONGODB_URI="mongodb+srv://synthetic:PRIVATE@cluster.example.mongodb.net/"\nMONGODB_DATABASE=from_file\nGEMINI_API_KEY=DO_NOT_LOAD\n')
            uri, name, local = check.load_configuration(path, {'MONGODB_DATABASE': 'from_process'})
            self.assertEqual(name, 'from_process')
            self.assertNotIn('DO_NOT_LOAD', uri)
            self.assertFalse(local)

    def test_driver_errors_and_credentials_are_withheld_from_cli_and_private_report(self):
        secret = 'DO_NOT_EXPORT_CREDENTIAL'
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'report.json'
            output = io.StringIO()
            with patch.dict(os.environ, {'MONGODB_URI': f'mongodb+srv://synthetic:{secret}@cluster.example.mongodb.net/', 'MONGODB_DATABASE': 'hackumass'}, clear=True), \
                 patch('sys.argv', ['atlas_preflight', '--report', str(report)]), \
                 patch.object(check, 'MongoClient', side_effect=ServerSelectionTimeoutError(secret)), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(check.main(), 1)
            self.assertNotIn(secret, output.getvalue() + report.read_text())
            self.assertEqual(report.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(report.read_text())['error_code'], 'CONNECTION_UNAVAILABLE')


@unittest.skipUnless(os.getenv('MONGODB_TEST_URI'), 'Set a disposable local replica-set URI.')
class PreflightDatabaseTests(unittest.TestCase):
    def test_read_only_checks_and_transaction_probe_preserve_existing_data(self):
        uri = os.environ['MONGODB_TEST_URI']
        name = 'adi_test_' + uuid4().hex
        with MongoClient(uri, serverSelectionTimeoutMS=3000, timeoutMS=10000) as client:
            database = client[name]
            try:
                apply_domain_drafts(database)
                database.unrelated_synthetic.insert_one({'_id': 'keep', 'value': 12})
                before = set(database.list_collection_names())
                read = check.preflight(uri, name, local=True)
                self.assertEqual(read['status'], 'completed')
                self.assertFalse(read['write_test_requested'])
                self.assertEqual(set(database.list_collection_names()), before)
                self.assertTrue(all(value['validator_matches'] and value['indexes_match'] for value in read['adi_schema_checks'].values()))
                self.assertFalse(read['core_migrations']['001_api_learning_runtime'])
                tested = check.preflight(uri, name, local=True, write_test=True, apply_owned_drafts=True)
                self.assertEqual(tested['status'], 'completed')
                self.assertTrue(tested['transaction_commit_verified'])
                self.assertTrue(tested['transaction_rollback_verified'])
                self.assertTrue(tested['probe_cleanup'])
                self.assertTrue(tested['owned_drafts_applied'])
                self.assertNotIn('probe_collection', tested)
                self.assertEqual(set(database.list_collection_names()), before)
                self.assertEqual(database.unrelated_synthetic.find_one({'_id': 'keep'})['value'], 12)
                with tempfile.TemporaryDirectory() as folder:
                    env = Path(folder) / '.env'
                    report = Path(folder) / 'report.json'
                    env.write_text(f'MONGODB_URI={uri}\nMONGODB_DATABASE={name}\n')
                    with patch.dict(os.environ, {}, clear=True), patch('sys.argv', ['atlas_preflight', '--env-file', str(env), '--report', str(report), '--allow-local-for-test', '--apply-owned-drafts', '--write-test']), contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(check.main(), 0)
                    self.assertTrue(json.loads(report.read_text())['probe_cleanup'])
                    self.assertEqual(report.stat().st_mode & 0o777, 0o600)
                self.assertEqual(set(database.list_collection_names()), before)
            finally:
                client.drop_database(name)

    def test_preflight_refuses_differing_validation_without_rewriting_existing_policy(self):
        uri = os.environ['MONGODB_TEST_URI']
        name = 'adi_test_' + uuid4().hex
        with MongoClient(uri, serverSelectionTimeoutMS=3000, timeoutMS=10000) as client:
            database = client[name]
            try:
                apply_domain_drafts(database)
                database.command('collMod', 'app_profiles', validationAction='warn')
                read = check.preflight(uri, name, local=True)
                self.assertFalse(read['adi_schema_checks']['app_profiles']['validator_matches'])
                apply = check.preflight(uri, name, local=True, apply_owned_drafts=True)
                self.assertEqual(apply['status'], 'failed')
                self.assertNotIn('owned_drafts_applied', apply)
                options = list(database.list_collections(filter={'name': 'app_profiles'}))[0]['options']
                self.assertEqual(options['validationAction'], 'warn')
            finally:
                client.drop_database(name)
