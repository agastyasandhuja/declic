# Election story: 3D template trial

Requested November 14, 2026: a new presidential-election video using the voxel
template, with 2D animation where useful. The author chose the U.S. Electoral
College, fictional orange/teal candidates and a three-state numerical example.
This is an authored topic adapter, not automatic arbitrary-topic 3D generation.

## What is reused, and what is new

- **Reused directly:** `../voxel-story/src/ModelKit.ts` is mounted read-only by
  `run.py`, not copied into this source tree. The existing Three.js module is
  SHA-256 pinned. `../../src/PopCaptions.tsx` supplies the approved white captions.
- **New:** civic plaza, ballot deposit, three miniature state stages, electoral
  token transfers, candidate reactions, 2D tallies and process diagrams.
- **Pipeline:** same validated script → cached voice/alignment → isolated render
  → full decode → encoded frame/motion inspection workflow. This independent
  adapter has its own closed 12-scene schema and output directory.
- **Authoring:** Codex wrote the script and geometry. No Claude/Astra call.
  Roger is a stock ElevenLabs narrator, not a public-figure voice clone.

## Fact review

Reviewed primary sources on November 14, 2026:

| Claim | Evidence / limit |
| --- | --- |
| Voters choose electors; 538 votes, 270 majority | [National Archives overview](https://www.archives.gov/electoral-college/about). This lesson uses the ordinary full-538 case. |
| State allocation = House seats + two; D.C. = three | [National Archives allocation](https://www.archives.gov/electoral-college/allocation). |
| 48 states and D.C. winner-take-all; Maine/Nebraska use statewide plus district winners | Same allocation source; explicitly avoid calling this proportional to each candidate's percentage. |
| Popular and electoral winners can differ | [National Archives FAQ](https://www.archives.gov/electoral-college/faq). |
| Electors vote in December; Congress counts in January | Archives overview. The animation is a process diagram, not a live election prediction. |
| No electoral majority: House chooses president, one vote per state delegation | Archives FAQ. Diagram specifies the top three electoral candidates. The Senate's separate vice-presidential choice is outside this short's scope. |

The toy states are explicitly fictional and equal-weight: A/B each have 51 teal
and 49 orange votes; C has 2 teal and 98 orange. Every state has five electors.
Totals: orange wins the popular count 196–104; teal wins electors 10–5.
They are not real state populations, a U.S. map, or an election forecast.

## Shot/action review plan

| Beat | Visible change |
| --- | --- |
| hook | Orange celebrates the popular tally; confetti falls; his arms lower and he looks toward teal. |
| ballot | Voter faces the box, reaches with a held ballot, releases it into the slot, and retracts the hand. |
| majority | A 538-mark diagram fills 270 marks. |
| allocation | Three House-seat blocks plus two Senator blocks rise; D.C.'s three are stated separately. |
| exceptions | Statewide/district distinction, with separate Maine/Nebraska token groups. |
| toy | Three miniature fictional state platforms appear. |
| narrow | Two 51–49 wins; ten distinct tokens travel from A/B into teal's tray. |
| landslide | The 98–2 win awards only C's five tokens to orange. |
| popular | Colored popular-vote bars resolve to 196 versus 104. |
| electoral | Electoral bars resolve to 5 versus 10; teal reacts. |
| certify | December → January diagram, then contingent House-election rule. |
| outro | Return to both candidates and the decisive electoral tally. |

All poses are deterministic. Animated tally blocks represent votes, not currency.
No source reference footage, game textures, party logos or candidate likenesses.

## Reproduce

Use the existing API venv, cached vendor module and renderer image:

```sh
PYTHONPATH=services/api services/api/.venv/bin/python services/renderer/experiments/election-story/prepare.py
python3 services/renderer/experiments/election-story/sound.py
python3 services/renderer/experiments/election-story/run.py stills
python3 services/renderer/experiments/election-story/run.py video
python3 services/renderer/experiments/election-story/finalize.py
python3 services/renderer/experiments/election-story/verify.py
```

Inspect stills before full rendering. Optional `--still-indices 1,14,29` restricts
stills for targeted repairs. The renderer remains non-root/read-only, offline,
without app credentials, and CPU/memory/time bounded. Narration reads credentials
only from existing server environment configuration, never scene data or source.
No certificate-validation changes; SHA-256 records artifact/dependency integrity.

Output: `.local/election-story/output/election-college/lesson.mp4`. Generated media
and caches stay ignored. `preview.py` stages both new trials in the local gallery
after their technical reports pass. Creative approval remains the user's decision;
physical iPhone playback and production-feed integration are separate checks.
