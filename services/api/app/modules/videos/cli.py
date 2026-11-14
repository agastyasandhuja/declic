import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .generation.providers import ElevenLabs, ProviderError
from .media import atomic_json
from .models import Brief
from .pipeline import ROOT, artifact_digests, generate, generation_recipe
from .rendering import render, validate_output


def main():
    parser = argparse.ArgumentParser(
        description="Local video generation; never publishes automatically"
    )
    parser.add_argument(
        "command",
        choices=[
            "generate",
            "preflight",
            "voices",
            "render",
            "validate",
            "enqueue",
            "worker",
            "publish",
        ],
    )
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument(
        "--brief", type=Path, default=ROOT / "fixtures/learning/revised-linked-list-brief.json"
    )
    parser.add_argument(
        "--format",
        choices=[
            "both",
            "visual_explainer",
            "dialogue_gameplay",
            "space_explainer",
            "math_explainer",
        ],
        default="both",
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Explicit local fake Claude/ElevenLabs; estimated captions",
    )
    parser.add_argument("--custom-scene", action="store_true")
    parser.add_argument("--storyboard-feedback", type=Path)
    parser.add_argument(
        "--scene-feedback",
        type=Path,
        help="Private visual review feedback for a bounded Claude repair",
    )
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / ".local/video-runs/linked-list")
    parser.add_argument(
        "--mongodb",
        action="store_true",
        help="Use configured Atlas instead of explicit local fake repository",
    )
    parser.add_argument(
        "--owner",
        default="user_demo_01",
        help="Trusted local administrator only; never accept this from mobile",
    )
    parser.add_argument("--job-id")
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=False)
    load_dotenv(ROOT / "services/api/.env", override=False)
    if args.command in {"enqueue", "worker", "publish"}:
        from .repository import AtlasVideoRepository, LocalVideoRepository
        from .service import run_once

        if args.mongodb:
            from pymongo import MongoClient

            client = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=10000)
            repository = AtlasVideoRepository(client[os.getenv("MONGODB_DATABASE", "hackumass")])
            repository.initialize()
        else:
            args.output.mkdir(parents=True, exist_ok=True)
            repository = LocalVideoRepository(args.output / "jobs.sqlite3")
        if args.command == "worker":
            print(
                json.dumps({"processed": run_once(repository, args.output, fixture=args.fixture)})
            )
            return
        if args.command == "publish":
            from .publication import SupabaseVideoStorage, publish_validated_variant

            if not args.job_id or not args.review:
                parser.error("publish requires --job-id and --review")
            review = json.loads(args.review.read_text())
            storage = SupabaseVideoStorage()
            storage.verify_private_bucket()
            job = repository.claim_review(args.job_id, args.owner, review.get("video_sha256"))
            if not job:
                parser.error("No matching reviewable job owned by this operator")
            work = args.output / job["job_id"]
            manifest = json.loads((work / "generation-manifest.json").read_text())
            try:
                variant = publish_validated_variant(
                    repository,
                    storage,
                    job,
                    Brief.model_validate(job["brief"]),
                    work,
                    manifest,
                    review,
                )
            except Exception:
                repository.update(job["job_id"], job["fence"], {"state": "awaiting_review"})
                raise
            print(json.dumps({"video_id": variant["video_id"], "status": variant["status"]}))
            return
    if args.command == "preflight":
        keys = [
            "ANTHROPIC_API_KEY",
            "ELEVENLABS_API_KEY",
            "ELEVENLABS_PETER_VOICE_ID",
            "ELEVENLABS_STEWIE_VOICE_ID",
            "ELEVENLABS_NARRATOR_VOICE_ID",
        ]
        print(
            json.dumps(
                {
                    "configured": {k: bool(os.getenv(k)) for k in keys},
                    "parkour": (ROOT / ".local/video-assets/parkour.mp4").exists(),
                },
                indent=2,
            )
        )
        return
    if args.command == "voices":
        data = ElevenLabs().voices()
        print(
            json.dumps(
                [
                    {"name": v["name"], "voice_id": v["voice_id"], "category": v.get("category")}
                    for v in data.get("voices", [])
                ],
                indent=2,
            )
        )
        return
    formats = ["visual_explainer", "dialogue_gameplay"] if args.format == "both" else [args.format]
    for fmt in formats:
        brief = Brief.model_validate_json(args.brief.read_text())
        brief = brief.model_copy(update={"format_id": fmt})
        work = args.output / fmt
        if args.command == "enqueue":
            if brief.scope == "private" and brief.owner_user_id != args.owner:
                parser.error("Brief owner differs from operator")
            recipe = generation_recipe(
                fixture=args.fixture, custom_scene=args.custom_scene and fmt == "visual_explainer"
            )
            key = brief.generation_key(recipe)
            job = repository.enqueue(
                key + (":" + args.owner if brief.scope == "shared_generic_candidate" else ""),
                args.owner,
                brief.model_dump(),
                recipe,
            )
            print(json.dumps({"format": fmt, "job_id": job["job_id"], "state": job["state"]}))
            continue
        if args.command in {"render", "validate"}:
            manifest = json.loads((work / "generation-manifest.json").read_text())
            report = (
                render(work / "pack", work / "output", args.preview)
                if args.command == "render"
                else validate_output(
                    work / "output",
                    args.preview,
                    minimum_duration=20 if fmt == "math_explainer" else 30,
                )
            )
            manifest.update(quality=report, artifact_digests=artifact_digests(work))
            atomic_json(work / "generation-manifest.json", manifest)
            print(json.dumps({"format": fmt, "quality": report}, indent=2))
            continue
        print(f"Generating {fmt}; {'fixture' if args.fixture else 'live'} mode", flush=True)
        result = generate(
            brief,
            work,
            fixture=args.fixture,
            preview=args.preview,
            custom_scene=args.custom_scene and fmt == "visual_explainer",
            render_video=not args.prepare_only,
            storyboard_feedback=args.storyboard_feedback.read_text()
            if args.storyboard_feedback
            else None,
            stage=lambda value: print(f"Stage: {value}", flush=True),
            scene_feedback=args.scene_feedback.read_text()
            if args.scene_feedback and fmt == "visual_explainer"
            else None,
        )
        print(
            json.dumps({"format": fmt, "status": result["status"], "output": str(work)}, indent=2)
        )


if __name__ == "__main__":
    try:
        main()
    except ProviderError as error:
        raise SystemExit(error.code) from None
