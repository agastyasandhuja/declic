# Generic demo lessons

24 original generic lessons, six each for the CS210, ACC233, HIS110 and MATH235
**demo** course labels. These are not scraped course materials, exam coverage
claims or private student records. Each lesson includes two server-side quiz
questions and factual support in `sources.json`. Never bundle answer keys in a
mobile pre-submission response.

The parent integration agent reviewed the generated scripts, facts, numerical
examples and all 48 correct answers/explanations. Content was initially authored
through the user's locally authenticated Claude Code subscription, then normalized
and corrected by Codex. No provider credentials or raw authoring response metadata
are included here. Actual per-video frame, continuous motion/audio and generic
publication reviews remain separate and bind final file hashes.

`lessons.json` is the reviewed source input for
`python -m app.modules.videos.local_demo validate/prepare`. `build_visuals.py`
retains deterministic authored scene rules and can regenerate scene data from
these normalized scripts with `--output /tmp/rebuilt.json`. Regenerated scenes
need fresh review; the script is not a factual verifier or automatic approval.
