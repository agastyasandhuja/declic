import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from app.core.migrate import definitions

ROOT = Path(__file__).resolve().parents[3]


def test_api_response_and_validator_artifacts_match_runtime(client):
    schemas = ROOT / "contracts/schemas/feed"
    session = client.post("/v1/feed/sessions", json={}).json()
    feed = client.get("/v1/feed", params={"session_id": session["session_id"]}).json()
    for name, response in [("SessionResponse", session), ("FeedResponse", feed)]:
        schema = json.loads((schemas / f"{name}.schema.json").read_text())
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(response)
    assert (
        json.loads((ROOT / "database/domains/learning/api-runtime-v1.json").read_text())
        == definitions()
    )


def test_public_openapi_does_not_publish_server_answer_definition(client):
    spec = client.get("/openapi.json").json()
    assert "correct_option_id" not in json.dumps(spec)
    assert "QuizDefinition" not in spec["components"]["schemas"]
    assert "/v1/feed" in spec["paths"]
    assert "/v1/quizzes/{quiz_instance_id}/answers" in spec["paths"]
    assert spec["paths"]["/v1/feed"]["get"]["security"] == [{"HTTPBearer": []}]
