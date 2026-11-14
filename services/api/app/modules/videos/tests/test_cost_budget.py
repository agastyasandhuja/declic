import json

import pytest

from app.modules.videos import pipeline
from app.modules.videos.generation.providers import Claude, ProviderError
from app.modules.videos.models import Brief


def test_default_model_is_lower_cost_and_per_job_budget_survives_restart(monkeypatch, tmp_path):
    monkeypatch.delenv("VIDEO_CLAUDE_MODEL", raising=False)
    monkeypatch.delenv("VIDEO_MAX_CLAUDE_CALLS", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic")
    monkeypatch.setenv("ELEVENLABS_NARRATOR_VOICE_ID", "synthetic")
    assert Claude().model == pipeline.generation_recipe()["claude"] == "claude-sonnet-4-5"
    requests = []

    class Model:
        def __init__(self, *, charge, **kwargs):
            self.charge = charge

        def storyboard(self, *args):
            for _ in range(7):
                self.charge()
                requests.append("synthetic request")

    monkeypatch.setattr(pipeline, "Claude", Model)
    monkeypatch.setattr(pipeline, "ElevenLabs", lambda: None)
    brief = Brief.model_validate_json(
        (pipeline.ROOT / "fixtures/learning/linked-list-brief.json").read_text()
    )
    for _ in range(2):
        with pytest.raises(ProviderError, match="AGENT_BUDGET_EXHAUSTED"):
            pipeline.generate(brief, tmp_path)
    assert len(requests) == 6
    assert json.loads((tmp_path / "budgets.json").read_text())["turns"] == 6
