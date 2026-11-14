# Zero Grip Zone — friction cartoon audition

A 43.5-second, 11-shot portrait cartoon requested by the user. A three-sneaker
shark loses traction; a coffee-cup driver's locked wheels fail to stop the car;
foam boxes stop it by contact force. The explanation reconnects the gag to
static traction and centripetal force, including `mv²/r ≤ μ_s N` and the
fourfold force demand at twice the speed for the same car and turn radius.

Status: **reviewed by the user; needs rework**, not an approved template.
The user found the animation and story inadequate, wanted straightforward
everyday consequences, preferred male voices, and rejected the excess branding,
scene labels and slogans. See [revision 2](../friction-story-v2/README.md).
The layered 2D artwork is authored Remotion/SVG animation with walk cycles,
facial poses, audio-envelope-driven mouths, locked and rolling wheels,
constant drift, a squash-and-stretch impact, camera cuts, aligned captions,
quiet original procedural music and five original foley cues. It is not
generative video or a production feed integration.

## Cast and writing

Opus (`claude-opus-5-5`) assessed supplied web evidence and wrote the initial
story/casting plan. The final script was tightened editorially to 102 words
and its final explanation raised to introductory university mechanics.
`storyboard.json` is the frozen reproducible script and casting source.

Three separate live ElevenLabs stock voices, `eleven_multilingual_v2`:

- Laura: playful female narrator.
- Charlie: energetic Australian shark.
- Callum: husky coffee-cup driver.

No celebrity voice imitation or downloaded meme audio. The stock descriptions
guided casting; a successful API call does not establish subjective performance
quality. Narration is leveled per utterance before mixing. Timing and mouth
motion use the returned alignment and measured audio envelope.

## Research and assumptions

The [character directory](https://www.virel.cc/ai-characters) supports the
established sneaker-shark / coffee-cup visual shorthand. The
[September search report](https://frutti.ai/ai-video-statistics) excludes TikTok
in-app searches. The [Jensen Huang template listing](https://www.makeviral.ai/templates/jensen-huang-ai-video)
is weak commercial trend evidence, so it did not determine this cast. None of
these establishes a verified current TikTok ranking. Opus evaluated the
provided evidence; it did not independently browse TikTok.

Physics references: OpenStax University Physics,
[friction](https://openstax.org/books/university-physics-volume-1/pages/6-2-friction)
and [centripetal force](https://openstax.org/books/university-physics-volume-1/pages/6-3-centripetal-force).
The fictional switch removes only shoe-ground and tire-road friction. Gravity
and normal/contact forces remain. The short coasting scene neglects air drag,
explicitly labeled on screen. The turning example assumes level pavement,
rolling without slipping, fixed mass and fixed radius.

## Reproduce

Run from repository root with existing configured server credentials. Never
copy `.env` into the render pack. No dependency installation is necessary.

```sh
# Optional: request a new Opus draft; inspect and deliberately update storyboard.json.
PYTHONPATH=services/api services/api/.venv/bin/python services/renderer/experiments/friction-story/plan.py

# The frozen script is authoritative for this exact audition.
PYTHONPATH=services/api services/api/.venv/bin/python services/renderer/experiments/friction-story/prepare.py
python3 services/renderer/experiments/friction-story/sound.py
python3 services/renderer/experiments/friction-story/run.py stills
python3 services/renderer/experiments/friction-story/run.py video
python3 services/renderer/experiments/friction-story/finalize.py
python3 services/renderer/experiments/friction-story/verify.py
python3 services/renderer/experiments/friction-story/check_motion.py
python3 services/renderer/experiments/friction-story/preview.py
```

The pinned existing renderer image runs with no network or credentials,
read-only root filesystem, non-root UID, bounded CPU/RAM/time, dropped
capabilities and only specific source/pack/output mounts. Renderer accepts
only the staged bounded scene/audio filenames. Outputs, provider caches,
usage records and QA reports remain ignored under `.local/friction-story`.

The current experimental authoring policy is in
[CREATIVE_DIRECTION.md](../CREATIVE_DIRECTION.md): vary voices, use stories when
they demonstrate the concept, and select college-level topics for future samples.
No global narrator setting or public API contract was changed.
