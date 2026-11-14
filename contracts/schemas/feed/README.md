# API-owned runtime schemas

Generated from FastAPI/Pydantic models by `scripts/export-api-contracts.py`.
Run that script using the API environment; `--check` detects drift. Do not edit
generated JSON directly. `openapi.json` contains only routes implemented by the
API/chat stream, not placeholder routes belonging to Adi, Amogh, or video generation.

Quiz cards and answer/recovery wire models are here to keep these files disjoint
from the video chat's internal generation schemas under `schemas/learning`.
Private quiz definitions and answer keys are intentionally not exported.

The entertainment shape is an allow-listed consumer projection of the existing
entertainment contract. Adi remains its owner. The internal academic candidate
projection is not a new academic wire schema. Unknown optional producer fields
are ignored; request bodies reject unknown fields.

Optional feed fields delivered: `availability` and each study item's
`constraint_relaxations`. These explain fallback/relaxation without changing v1
required fields or quiz-gating semantics. No public contract fields were renamed.
