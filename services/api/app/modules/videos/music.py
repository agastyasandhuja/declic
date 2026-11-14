"""Curated, licensed soundtrack retrieval. Models select IDs, never URLs."""

from pathlib import Path

import httpx

from .media import run, sha256

CATALOG = {
    "cylinder_six": {
        "title": "Cylinder Six",
        "number": "06",
        "mood": "restrained ambient electronic",
    },
    "cylinder_four": {
        "title": "Cylinder Four",
        "number": "04",
        "mood": "patient instrumental ambient",
    },
}


def stage_music(track_id: str, assets: Path, duration: float, *, fixture=False):
    if track_id not in CATALOG or not 20 <= duration <= 60:
        raise ValueError("Unknown soundtrack or invalid duration")
    assets.mkdir(parents=True, exist_ok=True)
    output = assets / "soundtrack.wav"
    if fixture:
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=220:sample_rate=48000",
                "-t",
                str(duration),
                "-af",
                "volume=0.12,loudnorm=I=-16:TP=-1:LRA=11",
                output,
            ]
        )
        return {"title": "Synthetic test tone", "fixture": True, "sha256": sha256(output)}
    track = CATALOG[track_id]
    url = f"https://audio.chriszabriskie.com/cylinders/cylinders-{track['number']}.m4a"
    raw = assets / "licensed-track.m4a"
    try:
        with httpx.Client(timeout=60, follow_redirects=False) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                total = 0
                with raw.open("wb") as file:
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > 20_000_000:
                            raise ValueError("Soundtrack byte limit exceeded")
                        file.write(chunk)
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-protocol_whitelist",
                "file,pipe",
                "-i",
                raw,
                "-t",
                str(duration),
                "-af",
                f"afade=t=in:d=0.4,afade=t=out:st={duration - 1.4}:d=1.4,"
                "loudnorm=I=-16:TP=-1:LRA=11",
                "-ar",
                "48000",
                "-ac",
                "2",
                output,
            ],
            timeout=90,
        )
        return {
            "track_id": track_id,
            "title": track["title"],
            "creator": "Chris Zabriskie",
            "album": "Cylinders",
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "source_url": "https://chriszabriskie.com/cylinders/",
            "permission_url": "https://chriszabriskie.com/use/",
            "download_url": url,
            "modifications": "Excerpt, fades and loudness normalization",
            "sha256": sha256(output),
        }
    finally:
        raw.unlink(missing_ok=True)
