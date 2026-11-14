# Instagram A2 experiment

The user selected Instagram and an existing account because account-specific
entertainment is required. TikTok-Api was researched, not live-tested. This local
probe tests account-session retrieval; it does not promise the exact native-app
recommendation stream or implement a production social-login flow.

## Run from the repository root

Python 3.11+ is required. Keep this experiment isolated from Agastya's shared API
dependencies; this is not the API service manifest or production dependency lock.

```sh
python3 -m venv .local/instagram-probe/venv
.local/instagram-probe/venv/bin/python -m pip install instagrapi==3.2.12
.local/instagram-probe/venv/bin/python services/api/app/modules/entertainment/experiments/instagram_probe.py
```

The program requires your own terminal and prompts privately for username,
password and an optional current 2FA code. Credentials go to Instagram through
instagrapi. It does not save passwords, cookies or session settings. Instagram
may require account verification; the probe stops at errors without automatic
checkpoint handling or transport retries. Review challenges in Instagram itself.
One SDK login call may include Instagram's instructed CAA/legacy fallback.
Do not paste credentials, codes or cookies into chat.

By default it requests one page of `clips/discover/` and keeps up to five Reels.
The library's public `explore_reels()` helper targets this same route, but swallows
some exceptions; this experiment calls the route directly to distinguish failure
from an empty feed. `--surface connected` chooses `clips/connected/` instead;
`--count` accepts 1–5. Run another surface only after reviewing the first result.
Requests use normal certificate verification, limited retries and per-request
timeouts; macOS/Linux also have a 180-second network-operation deadline.

No likes, follows, posts, messages, explicit seen-state writes or downloads are
performed. Normal login/feed requests can still affect Instagram's session state
and recommendations. A fresh account tests that account's own history, not yours.

## Results and boundaries

Ignored `.local/instagram-probe/report.json` contains only timestamps, library
version, stage, authentication status, counts and an error class if one occurs.
It deliberately excludes raw provider errors/responses and account identifiers.
`catalog.json` holds selected private local metadata and candidate video URLs,
with mode 0600; its directory is mode 0700. It is not a synthetic fixture and must
never be committed or shared as a public catalog.

A retrieved catalog completes the retrieval part of A2. Before claiming
personalization, the account owner must compare its creators/topics with the
account's usual recommendations; authenticated access alone is insufficient.
Video URL availability, expiry and actual iPhone playback need separate tests.
To view a successfully retrieved batch in the iOS Simulator, stop the normal
Metro server and run `npm run ios:instagram` from the repository root. See the
[mobile preview guide](../../../../../../apps/mobile/README.md#saved-instagram-preview-in-the-ios-simulator).
The mobile integration normalizes metadata and uses the existing player in a
localhost-only development preview. No Atlas persistence or FastAPI route is added.
Before serving a private feed to the app, finish A1's protected API authentication
and bind each app user to their own provider connection on the server.

Checks, from the repository root:

```sh
.local/instagram-probe/venv/bin/python -m unittest discover -s services/api/app/modules/entertainment/experiments -p 'test_*.py' -v
.local/instagram-probe/venv/bin/python -m pip check
```

References reviewed November 14, 2026:

- [Reels discovery implementation](https://github.com/subzeroid/instagrapi/blob/master/instagrapi/mixins/timeline.py)
- [Login and sessions](https://github.com/subzeroid/instagrapi/blob/master/docs/usage-guide/interactions.md)
- [Login migration and challenge handling](https://github.com/subzeroid/instagrapi/blob/master/docs/usage-guide/login-migration.md)
- [Meta's official Instagram Platform](https://developers.facebook.com/documentation/instagram-platform)

instagrapi is unofficial. Meta's documented professional-account APIs do not offer
a general personal recommended-Reels feed; this is an experiment, not a supported
official equivalent. Live results belong in docs/status/ADI.md.
