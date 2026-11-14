"""Exact-input cache behavior, exercised without provider traffic or billed calls."""

import json

import httpx
import pytest

from app.modules.videos.generation.providers import Claude, ProviderError
from app.modules.videos.models import ContentReview, RenderReview


@pytest.fixture
def cached_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    state = {"requests": [], "charges": [], "output": {"passed": True, "issues": []}}

    def handler(request):
        payload = json.loads(request.content)
        state["requests"].append(payload)
        return httpx.Response(
            200,
            json={
                "model": payload["model"],
                "usage": {"input_tokens": 12, "output_tokens": 8},
                "content": [
                    {
                        "type": "tool_use",
                        "name": "submit_stage_result",
                        "input": state["output"],
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:

        def factory(model="claude-opus-5-5", max_tokens=9000):
            return Claude(
                client=client,
                model=model,
                charge=lambda: state["charges"].append(1),
                cache_dir=tmp_path / "model-cache",
                max_tokens=max_tokens,
            )

        yield factory, state, tmp_path / "model-cache"


def test_response_budget_is_explicit_bounded_and_default_unchanged(cached_provider):
    factory, state, _ = cached_provider
    factory().structured(ContentReview, 'Default budget', {})
    factory(max_tokens=16000).structured(ContentReview, 'Story budget', {})
    assert [x['max_tokens'] for x in state['requests']]==[9000,16000]
    with pytest.raises(ValueError,match='max_tokens'):
        factory(max_tokens=1000000)


def test_identical_inputs_reuse_validated_disk_result_without_http_or_charge(cached_provider):
    factory, state, cache_dir = cached_provider
    first = factory()
    assert first.structured(ContentReview, "Review", {"topic": "geometry"}).passed
    # A fresh provider instance proves this is persistent disk reuse, not process state.
    second = factory()
    assert second.structured(ContentReview, "Review", {"topic": "geometry"}).passed
    assert len(state["requests"]) == len(state["charges"]) == 1
    assert len(list(cache_dir.glob("*.json"))) == 1
    assert second.usage == [{"model": "claude-opus-5-5", "cache_hit": True, "usage": {}}]
    assert first.usage[0]["usage"] == {"input_tokens": 12, "output_tokens": 8}


@pytest.mark.parametrize("changed", ["payload", "system", "attachment", "model", "schema"])
def test_changed_generation_input_cannot_reuse_previous_result(cached_provider, changed):
    factory, state, cache_dir = cached_provider
    attachments = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "AA=="}}
    ]
    args = {
        "schema": ContentReview,
        "system": "Review",
        "payload": {"topic": "geometry"},
        "attachments": attachments,
    }
    provider = factory()
    provider.structured(**args)
    if changed == "payload":
        args["payload"] = {"topic": "biology"}
    elif changed == "system":
        args["system"] = "Review under revised style rules"
    elif changed == "attachment":
        # Same metadata and text, different actual image bytes.
        attachments[0]["source"]["data"] = "AQ=="
    elif changed == "model":
        provider = factory(model="claude-sonnet-4-5")
    else:
        args["schema"] = RenderReview
    provider.structured(**args)
    assert len(state["requests"]) == len(state["charges"]) == 2
    assert len(list(cache_dir.glob("*.json"))) == 2
    assert not provider.usage[-1].get("cache_hit")


def test_cache_hit_rechecks_semantics_and_cannot_bypass_new_validation(cached_provider):
    factory, state, _ = cached_provider
    provider = factory()
    provider.structured(ContentReview, "Review", {"topic": "geometry"})
    checked = []

    def reject_under_new_rules(result):
        checked.append(result)
        raise ValueError("New semantic rule rejects this result")

    with pytest.raises(ValueError, match="New semantic rule"):
        provider.structured(
            ContentReview,
            "Review",
            {"topic": "geometry"},
            validate=reject_under_new_rules,
        )
    assert len(checked) == 1
    assert isinstance(checked[0], ContentReview)
    assert len(state["requests"]) == len(state["charges"]) == 1
    assert not any(item.get("cache_hit") for item in provider.usage)


@pytest.mark.parametrize("failure", ["schema", "semantic"])
def test_rejected_model_results_are_not_cached_and_later_valid_result_can_succeed(
    cached_provider, failure
):
    factory, state, cache_dir = cached_provider
    provider = factory()

    def require_pass(result):
        if not result.passed:
            raise ValueError("Review failed semantic requirement")
        return result

    state["output"] = (
        {"passed": "not-a-boolean", "issues": []}
        if failure == "schema"
        else {"passed": False, "issues": ["A blocking issue"]}
    )
    with pytest.raises(ProviderError, match="CLAUDE_SCHEMA_REPAIR_EXHAUSTED"):
        provider.structured(ContentReview, "Review", {}, validate=require_pass)
    assert len(state["requests"]) == len(state["charges"]) == 3
    assert not list(cache_dir.glob("*.json"))
    state["output"] = {"passed": True, "issues": []}
    assert provider.structured(ContentReview, "Review", {}, validate=require_pass).passed
    assert len(state["requests"]) == len(state["charges"]) == 4
    assert len(list(cache_dir.glob("*.json"))) == 1
