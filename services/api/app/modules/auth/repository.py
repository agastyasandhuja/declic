"""Owned profile persistence. Inject a Database from Agastya's shared client."""
from functools import wraps
from pymongo.errors import PyMongoError

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from .service import AuthFailure


def storage_errors(function):
    @wraps(function)
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except PyMongoError:
            raise AuthFailure(503, 'PROFILE_UNAVAILABLE', 'Profile storage is unavailable. Retry shortly.') from None
    return call


class ProfileRepository:
    def __init__(self, database):
        self.collection = database['app_profiles']

    @storage_errors
    def get_profile(self, user):
        stored = self.collection.find_one({'user_id': user['user_id']}, {'_id': 0})
        if not stored:
            return {**user, 'revision': 0}
        return {**user, 'display_name': stored['display_name'], 'timezone': stored['timezone'], 'revision': stored['revision']}

    @storage_errors
    def update_profile(self, user, expected_revision, changes):
        if type(expected_revision) is not int or expected_revision < 0 or not changes or set(changes) - {'display_name', 'timezone'}:
            raise AuthFailure(422, 'INVALID_PROFILE', 'Only display name and timezone can be changed.')
        if 'display_name' in changes and changes['display_name'] is not None and (not isinstance(changes['display_name'], str) or len(changes['display_name']) > 80):
            raise AuthFailure(422, 'INVALID_PROFILE', 'Display name must have at most 80 characters.')
        if 'timezone' in changes:
            try:
                if not isinstance(changes['timezone'], str):
                    raise ValueError()
                ZoneInfo(changes['timezone'])
            except (ValueError, ZoneInfoNotFoundError):
                raise AuthFailure(422, 'INVALID_PROFILE', 'Choose a valid IANA timezone.') from None
        now = datetime.now(timezone.utc)
        fields = {**changes, 'updated_at': now}
        initial = {'schema_version': '1', 'created_at': now}
        for key, default in (('display_name', None), ('timezone', 'UTC')):
            if key not in changes:
                initial[key] = default
        try:
            result = self.collection.find_one_and_update(
                {'user_id': user['user_id'], 'revision': expected_revision} if expected_revision else {'user_id': user['user_id'], 'revision': {'$exists': False}},
                {'$set': fields, '$setOnInsert': initial, '$inc': {'revision': 1}},
                upsert=expected_revision == 0, return_document=ReturnDocument.AFTER)
        except DuplicateKeyError:
            result = None
        if result is None:
            raise AuthFailure(409, 'STALE_REVISION', 'Your profile changed. Reload it before saving.')
        return {**user, 'display_name': result['display_name'], 'timezone': result['timezone'], 'revision': result['revision']}
