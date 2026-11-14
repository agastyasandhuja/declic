"""Local A2 experiment: fetch account-session Reels without logging credentials.

Run in the isolated environment documented beside this file. This is not an API
route, an OAuth integration, or proof of native playback/personalization parity.
"""
from __future__ import annotations

import argparse
import contextlib
import getpass
import json
import logging
import os
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import signal
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[6]
OUTPUT = ROOT / ".local" / "instagram-probe"


def write_private(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(path)


@contextlib.contextmanager
def quiet_provider():
    # Provider logs/errors can include headers, cookies or unfiltered responses.
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with open(os.devnull, "w") as sink:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                yield
    finally:
        logging.disable(previous)


def summarize_media(items: list) -> list[dict]:
    """Keep only catalog metadata, never account/session or raw provider payloads."""
    seen = set()
    result = []
    for item in items:
        if item.media_type != 2 or item.product_type != "clips":
            continue
        identifier = str(item.pk)
        if identifier in seen:
            continue
        seen.add(identifier)
        url = str(item.video_url) if item.video_url else None
        result.append({
            "provider_video_id": identifier,
            "source_url": f"https://www.instagram.com/reel/{item.code}/",
            "creator_handle": item.user.username,
            "caption": item.caption_text,
            "duration_seconds": item.video_duration,
            "candidate_playback_url": url if url and url.startswith("https://") else None,
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface", choices=("discover", "connected"), default="discover")
    parser.add_argument("--count", type=int, choices=range(1, 6), default=5)
    args = parser.parse_args()
    if not sys.stdin.isatty():
        parser.error("Run in your own terminal; credentials must use hidden prompts.")

    from instagrapi import Client

    report = {
        "provider": "instagram", "library": "instagrapi", "version": version("instagrapi"),
        "surface": args.surface, "requested": args.count, "stage": "awaiting_credentials",
        "authenticated": False, "retrieved": 0, "https_candidates": 0,
        "personalization_verified": False, "native_playback_verified": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    write_private(OUTPUT / "report.json", report)
    print("Instagram account-session Reels test. Credentials are sent only to Instagram.")
    print("Login may require approval in Instagram. No passwords or session files are saved.")
    username = getpass.getpass("Instagram username (hidden): ").strip()
    password = getpass.getpass("Instagram password (hidden): ")
    code = getpass.getpass("Current 2FA code, or Enter if disabled (hidden): ").strip()
    if not username or not password:
        report["stage"] = "cancelled"
        write_private(OUTPUT / "report.json", report)
        print("Cancelled: username and password are required.")
        return 1

    client = None
    old_alarm = None
    def stop_on_provider_error(_client, error):
        raise error
    def deadline(_signum, _frame):
        raise TimeoutError("Probe deadline")
    try:
        print("Making one SDK login call, then one small Reels request…", flush=True)
        report["stage"] = "login"
        write_private(OUTPUT / "report.json", report)
        if hasattr(signal, "SIGALRM"):
            old_alarm = signal.signal(signal.SIGALRM, deadline)
            signal.alarm(180)
        with quiet_provider():
            client = Client(settings={"session_retry_total": 0, "public_request_retries_count": 1})
            client.handle_exception = stop_on_provider_error
            for session in (client.private, client.public):
                original = session.request
                def bounded(*a, _request=original, **kw):
                    if kw.get("timeout") is None:
                        kw["timeout"] = (10, 30)
                    return _request(*a, **kw)
                session.request = bounded
            accepted = client.login(username, password, verification_code=code)
            if not accepted or not client.user_id:
                raise RuntimeError("No authenticated session")
            report["authenticated"] = True
            report["stage"] = "retrieve"
            write_private(OUTPUT / "report.json", report)
            # The high-level helper can swallow endpoint errors. Propagate them
            # instead so a provider failure cannot be reported as an empty feed.
            endpoint = "clips/discover/" if args.surface == "discover" else "clips/connected/"
            response = client.private_request(endpoint, data=" ", params={"max_id": ""})
            from instagrapi.extractors import extract_media_v1
            raw_items = response.get("items") or response.get("items_with_ads") or []
            media = [extract_media_v1(item["media"]) for item in raw_items if item.get("media")]
            catalog = summarize_media(media)[:args.count]
        report["retrieved"] = len(catalog)
        report["https_candidates"] = sum(bool(item["candidate_playback_url"]) for item in catalog)
        report["stage"] = "retrieved" if catalog else "empty"
        # This private local catalog is not a fixture and must never be committed.
        write_private(OUTPUT / "catalog.json", {"acquired_at": datetime.now(timezone.utc).isoformat(), "surface": args.surface, "items": catalog})
        print(f"Authenticated; retrieved {len(catalog)} Reels with {report['https_candidates']} HTTPS video candidates.")
        print("Inspect .local/instagram-probe/catalog.json locally to compare with your Instagram recommendations.")
        print("Matching your native feed and playing in Expo are still separate, unverified checks.")
        return 0 if catalog else 2
    except (Exception, KeyboardInterrupt) as error:
        report["stage"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        report["error_type"] = type(error).__name__
        print(f"Stopped ({type(error).__name__}). No automatic checkpoint resolution or application-level retries.")
        print("For a challenge, review Instagram on your phone. Raw errors are withheld to protect credentials.")
        return 1
    finally:
        password = code = ""
        if old_alarm is not None:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_alarm)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_private(OUTPUT / "report.json", report)
        if client is not None:
            for session in (client.private, client.public):
                with quiet_provider(), contextlib.suppress(Exception):
                    session.close()


if __name__ == "__main__":
    raise SystemExit(main())
