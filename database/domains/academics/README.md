# Academics collection draft — Amogh

manifest.json defines three collections, all keyed by the app user's `user_id`:

- `academic_profiles`: the current AcademicProfile per user (unique `user_id`).
- `academic_profile_revisions`: every saved revision (unique `user_id` + `revision`).
- `academic_lesson_plans`: the user's current lesson plans (unique `user_id`).

The repository (`app/modules/curriculum/atlas_store.py`) filters every read and
write by `user_id` and refuses documents whose embedded owner differs. No Canvas
tokens, Gemini keys or raw file bytes are stored, only the validated profile.

Install (additive; never drops data or indexes; refuses a conflicting validator):

    PYTHONPATH=services/api services/api/.venv/bin/python -m app.modules.curriculum.atlas_store --apply --env-file services/api/.env

Agastya integrates this draft into ordered migrations. No backfill is needed:
academic data previously lived only in each developer's local `.local/academics`.
