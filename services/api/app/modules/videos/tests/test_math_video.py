import json

import httpx
import pytest

from app.modules.videos.generation.providers import Claude
from app.modules.videos.math_video import matrix_plan
from app.modules.videos.models import Brief, ContentReview
from app.modules.videos.music import stage_music
from app.modules.videos.pipeline import ROOT


def test_reference_examples_and_non_square_dot_products():
    plan, duration = matrix_plan([[1, 3], [5, 7]], [[2, 4], [6, 8]])
    assert [c["result"] for c in plan["cells"]] == [20, 28, 52, 76]
    assert duration == 21
    plan, _ = matrix_plan([[6, 2, 9], [8, 7, 4]], [[5, 3], [2, 8], [6, 1]])
    assert [c["result"] for c in plan["cells"]] == [88, 43, 78, 84]
    plan, _ = matrix_plan([[0, -1], [-2, 3]], [[-2, 4], [5, 0]])
    assert [c["result"] for c in plan["cells"]] == [-5, 0, 19, -8]


@pytest.mark.parametrize("matrix", [[], [[1], [2]], [[1, 2], [3]], [[10, 2], [3, 4]]])
def test_brief_rejects_unrenderable_matrix(matrix):
    raw = json.loads((ROOT / "fixtures/learning/matrix-math-brief.json").read_text())
    raw["matrix_a"] = matrix
    with pytest.raises(ValueError):
        Brief.model_validate(raw)


def test_music_model_cannot_supply_url(tmp_path):
    with pytest.raises(ValueError, match="Unknown"):
        stage_music("https://127.0.0.1/private", tmp_path, 34)


def test_opus_uses_auto_tools_and_preserves_response_model(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    monkeypatch.delenv("VIDEO_CLAUDE_MODEL", raising=False)
    monkeypatch.setenv("CLAUDE_MODEL", "claude-sonnet-4-5")
    seen = []

    def handler(request):
        data = json.loads(request.content)
        seen.append(data)
        return httpx.Response(
            200,
            json={
                "model": "claude-opus-5-5",
                "usage": {},
                "content": [
                    {
                        "type": "tool_use",
                        "name": "submit_stage_result",
                        "input": {"passed": True, "issues": []},
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        model = Claude(client=client)
        assert model.structured(ContentReview, "Return review", {}).passed
    assert seen[0]["model"] == "claude-opus-5-5"
    assert seen[0]["tool_choice"] == {"type": "auto"}
    assert model.usage[0]["model"] == "claude-opus-5-5"
