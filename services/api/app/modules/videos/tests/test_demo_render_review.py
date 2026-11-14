"""Explicit renderer approval must survive no unreviewed content mutation."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def batch_runner(monkeypatch):
    root = Path(__file__).resolve().parents[6]
    folder = root / "services/renderer/experiments/demo-library"
    monkeypatch.syspath_prepend(str(folder))
    spec = importlib.util.spec_from_file_location("demo_batch_runner", folder / "batch_render.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "source_digest", lambda: "renderer_v1")
    yield module
    sys.modules.pop("run", None)


def test_frame_approval_binds_source_pack_and_every_actual_frame(tmp_path, batch_runner):
    runner = batch_runner
    pack = tmp_path / "pack/demo_one"
    output = tmp_path / "output/demo_one"
    approval = tmp_path / "approvals/demo_one.json"
    pack.mkdir(parents=True)
    output.mkdir(parents=True)
    approval.parent.mkdir()
    (pack / "lesson.json").write_text('{"id":"demo_one"}')
    (pack / "manifest.json").write_text('{"files":{}}')
    (output / "frame-00.png").write_bytes(b"reviewed-frame-bytes")
    (output / "frame-index.json").write_text('[{"file":"frame-00.png"}]')
    assert not runner.approved(tmp_path, "demo_one")
    evidence = {
        "reviewer": "codex",
        "frames_reviewed": True,
        "provenance": runner.expected(tmp_path, "demo_one"),
        "frames": runner.frames(tmp_path, "demo_one"),
    }
    approval.write_text(json.dumps(evidence))
    assert runner.approved(tmp_path, "demo_one")
    (output / "frame-00.png").write_bytes(b"different-frame")
    assert not runner.approved(tmp_path, "demo_one")
    (output / "frame-00.png").write_bytes(b"reviewed-frame-bytes")
    (pack / "lesson.json").write_text('{"id":"changed"}')
    assert not runner.approved(tmp_path, "demo_one")
    (pack / "lesson.json").write_text('{"id":"demo_one"}')
    evidence["provenance"]["renderer_source"] = "old-renderer"
    approval.write_text(json.dumps(evidence))
    assert not runner.approved(tmp_path, "demo_one")


def test_cached_video_needs_exact_validated_final_bytes(tmp_path, batch_runner):
    runner = batch_runner
    pack, output = tmp_path / "pack/demo_one", tmp_path / "output/demo_one"
    pack.mkdir(parents=True)
    output.mkdir(parents=True)
    for name in ("lesson.json", "manifest.json"):
        (pack / name).write_text("{}")
    (output / "lesson.mp4").write_bytes(b"video")
    (output / "video-provenance.json").write_text(json.dumps(runner.expected(tmp_path, "demo_one")))
    (output / "quality.json").write_text(
        json.dumps({"media_checks": "passed", "sha256": runner.sha(output / "lesson.mp4")})
    )
    assert runner.current(tmp_path, "demo_one", "video")
    (output / "lesson.mp4").write_bytes(b"changed-video")
    assert not runner.current(tmp_path, "demo_one", "video")
