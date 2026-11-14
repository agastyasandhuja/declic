# 006 — Video quality revision and music-led math template

Date: 2026-11-14. Implemented locally in Agastya's stream at the user's request;
mobile integration, publication, and iPhone playback are not implied.

Keep Remotion as the frame renderer and the Python harness as orchestrator. No new
service or JavaScript dependency. Preserve `guided_v1` and `reference_v2` artifacts;
new Brief defaults are `reference_v3` and template `3.0.0`.

## Interface and integration impact

- Add `math_explainer` to the backend learning/feed format enum. Existing feed cards
  still carry ordinary video assets. Adi may add a display label/filter when needed;
  this change does not install navigation or claim a mobile category is integrated.
- Add optional internal Brief `matrix_a` / `matrix_b`: compatible rectangular
  integer matrices with 2–3 rows/columns and entries −9…9. Required only for math.
  This first math template supports matrix multiplication, not arbitrary mathematics.
- Math uses a separate `MathDirection`, trusted integer dot products, timed cells,
  `audio_mode=music`, and a staged `soundtrack.wav`. No fake narration transcript.
  Renderer independently recomputes products and sums. Existing spoken formats keep
  their narration, captions and semantic trace.
- `VIDEO_CLAUDE_MODEL` defaults to `claude-opus-5-5` independently of a generic
  `CLAUDE_MODEL`. Opus 5.5 requires auto tool selection; returned tool arguments
  still undergo the same schema/semantic validation and bounded repairs.
- `reference_v3` photo lessons need four distinct images, no adjacent reuse, and
  at most two uses per image. Actual source/content/perceptual duplication is
  rejected. The selector inspects candidate pixels before choosing; final framing
  review remains separate. Downloads remain raster-only, allowlisted and bounded.
- Space plans need four distinct demonstrations, with no adjacent repeated mode.
  New authored modes use different geometry for gravity, hierarchy, filaments,
  galaxies and light travel. Camera movement does not count as scene diversity.
- Dialogue uses dark overlays, short corrective exchanges and at least two snarky
  Stewie replies. The user's requested modest pacing increase uses 1.08× audio
  tempo and remaps word timestamps, events and character amplitude to that audio.
- New live generation renders sampled frames first and asks Opus to inspect them.
  Rejected drafts stop before final MP4 rendering. This is an assistive visual
  gate, not proof of smooth motion, accurate audio, improved learning or engagement.

## Music and boundaries

The model selects from a curated two-track catalog; it cannot submit download URLs.
The worker retrieves from the composer's official audio host with redirects disabled,
a 20 MB cap and local-only decoding. Both tracks are from Chris Zabriskie's Cylinders,
licensed CC BY 4.0. Manifest records source, license, attribution and modifications;
a CREDITS.txt sidecar accompanies the minimal math clip. Reference video soundtracks are not reused.

- [Composer's album](https://chriszabriskie.com/cylinders/)
- [Composer's permission and attribution](https://chriszabriskie.com/use/)
- [Opus 5.5 migration](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide)
- [Flickr's documented image sizes](https://www.flickr.com/services/api/misc.urls.html)

All generated scenes still run without app credentials or network access in the
bounded Docker renderer. No production upload, database change or provider credential
is part of this patch. Keep generated media and local run diagnostics out of Git.

## Minimal math refinement after user review

The user rejected small matrices, instructional text, and a persistent music footer.
The revised renderer shows one title and mathematical symbols only, enlarges source
numerals from 54 to 88 px for 2×2 inputs, and uses a 1.5-second opening, four 4.5-second
cell demonstrations and 1.5-second ending (21 seconds). Music attribution moves to
CREDITS.txt and the manifest; include it in the description when sharing. The next
publisher integration must carry those credits rather than discarding the sidecar.
The math duration bounds become 20–60 seconds; spoken formats remain 30–60. This is
a format-specific pacing preference, not a claim of better learning from faster speech.
