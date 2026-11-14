# Friction — direct everyday examples, revision 2

Rebuilt after the user rejected the first cartoon's story, animation and excess
text. Twelve shots, about 45 seconds: cars collide; a woman walking her dog loses
her footing and the dog also slides; a phone slips from a pinching hand; a gym
climber slides down a rope onto a mat. Then moving diagrams demonstrate sliding
friction, the action/reaction pair in walking, loss of traction, a car continuing
along a tangent, and the `v²` dependence of turning-force demand.

The lead is **Liam**, with **Roger** for one short gym reaction. Both are live
ElevenLabs male stock voices. The frozen 115-word script follows the user's
requested structure. There is no music, only three quiet original contact sounds.

All visible writing is speech captions or essential diagram notation:
`F`, `v`, `F = 0`, `2v`, `4F`, `F = mv²/r`. No titles, badges, character labels,
branding, slogans or footers. Scenes use layered 2D artwork, articulated humans,
a dog walk/slip cycle, locked car wheels, collision-induced motion, a falling
phone and rope climber, and continuous curve-to-tangent car motion.

The user endorsed this **story direction as promising**, while noting that some
animation still needs work. This is not a claim that all animation concerns are
solved or that every new generated story will be funny. The latest revision adds
the shared phrase-pop captions and completes the woman's supported landing pose.

## Reproduce from repository root

```sh
PYTHONPATH=services/api services/api/.venv/bin/python services/renderer/experiments/friction-story-v2/prepare.py
python3 services/renderer/experiments/friction-story-v2/sound.py
python3 services/renderer/experiments/friction-story-v2/run.py stills
python3 services/renderer/experiments/friction-story-v2/run.py video
python3 services/renderer/experiments/friction-story-v2/finalize.py
python3 services/renderer/experiments/friction-story-v2/verify.py
python3 services/renderer/experiments/friction-story-v2/check_motion.py
python3 services/renderer/experiments/friction-story-v2/preview.py
```

Provider credentials stay outside the existing network-disabled, non-root,
resource-limited renderer. All media and provider cache remain ignored under
`.local/friction-story-v2`. Sample 21 is added to the local gallery while the
previous attempt and browser feedback remain available for comparison.

The counterfactual sets tangential contact friction to zero while retaining
gravity, normal forces and rigid assemblies. Short slides neglect air drag.
The ordinary friction-present comparison is introduced by “normally.” The final
turning-force comparison holds mass and radius fixed. References:
[OpenStax friction](https://openstax.org/books/university-physics-volume-1/pages/6-2-friction)
and [centripetal force](https://openstax.org/books/university-physics-volume-1/pages/6-3-centripetal-force).

See [current creative direction](../CREATIVE_DIRECTION.md) for the user's
male-voice, straightforward-story, minimal-text and college-level preferences.
