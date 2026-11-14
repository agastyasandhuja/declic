import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from app.modules.videos.generation.providers import Claude, ElevenLabs, ProviderError
from app.modules.videos.media import contained
from app.modules.videos.models import Brief, Storyboard
from app.modules.videos.narration.timing import alignment_words, caption_groups, resolve_cue, vtt
from app.modules.videos.pipeline import ROOT
from app.modules.videos.publication import publish_validated_variant
from app.modules.videos.repository import LocalVideoRepository, StaleLease


@pytest.fixture
def brief():
    return Brief.model_validate_json(
        (ROOT / "fixtures/learning/linked-list-brief.json").read_text()
    )


@pytest.fixture
def board(brief):
    return Storyboard.model_validate_json(
        (ROOT / "fixtures/learning/visual_explainer.json").read_text()
    ).validate_for(brief)


def test_fixture_contracts(brief):
    for fmt in ("visual_explainer", "dialogue_gameplay"):
        selected = brief.model_copy(update={"format_id": fmt})
        Storyboard.model_validate_json(
            (ROOT / f"fixtures/learning/{fmt}.json").read_text()
        ).validate_for(selected)


def test_reject_wrong_pointer_trace(brief, board):
    board.events[1], board.events[2] = board.events[2], board.events[1]
    with pytest.raises(ValueError, match="save, reverse"):
        board.validate_for(brief)


def test_reject_unresolved_cue(brief, board):
    board.events[1].cue.phrase = "invented speech"
    with pytest.raises(ValueError, match="phrase"):
        board.validate_for(brief)


def test_scope_separates_private_cache(brief):
    a = brief.model_copy(update={"scope": "private", "owner_user_id": "alice"})
    b = a.model_copy(update={"owner_user_id": "bob"})
    assert a.generation_key({}) != b.generation_key({})
    assert "owner_user_id" not in a.teaching_payload()
    assert a.generation_key({"voice": "a"}) != a.generation_key({"voice": "b"})


def alignment(text):
    return {
        "characters": list(text),
        "character_start_times_seconds": [i * 0.1 for i in range(len(text))],
        "character_end_times_seconds": [(i + 1) * 0.1 for i in range(len(text))],
    }


@pytest.mark.parametrize("failure", ["length", "nan", "negative", "past_audio", "unordered"])
def test_bad_alignment_rejected(failure):
    a = alignment("hello world")
    if failure == "length":
        a["characters"].pop()
    if failure == "nan":
        a["character_start_times_seconds"][2] = float("nan")
    if failure == "negative":
        a["character_start_times_seconds"][0] = -0.1
    if failure == "past_audio":
        a["character_end_times_seconds"][-1] = 99
    if failure == "unordered":
        a["character_start_times_seconds"][5] = 0.01
    with pytest.raises(ValueError):
        alignment_words(a, 1.1)


def test_word_offsets_captions_and_speakers():
    first = alignment_words(alignment("Save next"), 0.9, 1, "peter")
    second = alignment_words(alignment("Then reverse"), 1.2, 2, "stewie")
    assert first[1]["start"] == 1.5
    groups = caption_groups(first + second)
    assert len(groups) == 2
    assert "00:00:01.000 --> 00:00:01.900" in vtt(groups)
    assert all(len({w["speaker"] for w in g["words"]}) == 1 for g in groups)


def test_exact_cue_resolution(board):
    segment = board.segments[1]
    words = alignment_words(alignment(segment.spoken_text), len(segment.spoken_text) * 0.1, 5)
    cue = board.events[1].cue
    assert resolve_cue(cue, segment, words) == 5


def test_trusted_trace_preserves_prior_reversals_and_saved_successor(brief, board):
    from app.modules.videos.trace import linked_list_trace

    events = [
        {"action": event.action, "node": event.node, "time": index}
        for index, event in enumerate(board.events)
    ]
    states = linked_list_trace(brief.input_values, events)
    assert states[2]["links"] == [None, 2, None]
    assert states[3]["current"] == 1
    assert states[4]["saved_next"] == 2
    assert states[5]["links"] == [None, 0, None]
    assert states[6]["current"] == 2
    assert states[-1]["head"] == 2
    assert states[-1]["current"] is None
    assert states[-1]["links"] == [None, 0, 1]


def test_manifest_containment(tmp_path):
    (tmp_path / "ok").write_text("ok")
    (tmp_path / "escape").symlink_to("/etc/passwd")
    assert contained(tmp_path, "ok") == tmp_path / "ok"
    for bad in ("../passwd", "/etc/passwd", "escape"):
        with pytest.raises(ValueError):
            contained(tmp_path, bad)


def test_concurrent_enqueue_and_restart(tmp_path):
    path = tmp_path / "jobs.db"
    repo = LocalVideoRepository(path)
    with ThreadPoolExecutor(max_workers=6) as executor:
        jobs = list(executor.map(lambda _: repo.enqueue("same", "alice", {}, {}), range(12)))
    assert len({j["job_id"] for j in jobs}) == 1
    assert LocalVideoRepository(path).claim(now=1)["job_id"] == jobs[0]["job_id"]
    assert repo.get(jobs[0]["job_id"], "bob") is None


def test_stale_worker_and_cancel_cannot_publish(tmp_path):
    repo = LocalVideoRepository(tmp_path / "jobs.db")
    repo.enqueue("same", "alice", {}, {})
    first = repo.claim(now=1, lease=10)
    second = repo.claim(now=12)
    with pytest.raises(StaleLease):
        repo.publish(first["job_id"], first["fence"], {}, now=13)
    assert repo.cancel(second["job_id"], "bob") is False
    assert repo.cancel(second["job_id"], "alice") is True
    with pytest.raises(StaleLease):
        repo.publish(second["job_id"], second["fence"], {}, now=13)


def test_publication_and_outbox_are_atomic(tmp_path):
    repo = LocalVideoRepository(tmp_path / "jobs.db")
    repo.enqueue("same", "alice", {}, {})
    job = repo.claim(now=1)
    with pytest.raises(KeyError):
        repo.publish(job["job_id"], job["fence"], {"video_id": "broken"}, now=2)
    assert repo.get(job["job_id"], "alice")["state"] == "running"
    variant = {
        "video_id": "video",
        "generation_key": "same",
        "status": "ready",
        "scope": "private",
        "owner_user_id": "alice",
        "lesson_request_id": "req",
        "objective_id": "obj",
    }
    repo.publish(job["job_id"], job["fence"], variant, now=2)
    assert repo.ready("same", "alice")
    assert repo.ready("same", "bob") is None
    with repo.transaction() as c:
        assert c.execute("SELECT count(*) FROM outbox").fetchone()[0] == 1


def test_unreviewed_fixture_never_uploads(brief, tmp_path):
    class NeverStorage:
        def verify_private_bucket(self):
            pytest.fail("Must not contact storage")

    with pytest.raises(ValueError, match="human approval"):
        publish_validated_variant(
            None, NeverStorage(), {}, brief, tmp_path, {"fixture": True, "quality": {}}, {}
        )


def test_claude_repairs_invalid_output(monkeypatch, brief, board):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-test-key")
    calls = []

    def respond(request):
        payload = json.loads(request.content)
        calls.append(payload)
        result = board.model_dump() if len(calls) > 1 else {"wrong": True}
        return httpx.Response(
            200,
            json={
                "model": "test",
                "content": [{"type": "tool_use", "name": "submit_stage_result", "input": result}],
            },
        )

    provider = Claude(client=httpx.Client(transport=httpx.MockTransport(respond)))
    result = provider.storyboard(brief, ROOT / "services/renderer/templates")
    assert result == board and len(calls) == 2
    assert calls[0]["tools"][0]["name"] == "submit_stage_result"
    assert "owner_user_id" not in calls[0]["messages"][0]["content"]


def test_provider_auth_failure_is_not_retried(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "synthetic-test-key")
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(401, json={"secret": "must not escape"})

    provider = ElevenLabs(client=httpx.Client(transport=httpx.MockTransport(respond)))
    with pytest.raises(ProviderError, match="PROVIDER_HTTP_401") as error:
        provider.voices()
    assert len(calls) == 1 and "secret" not in str(error.value)
