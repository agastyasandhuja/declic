# Spinning chair: 2D cartoon template trial

Requested alongside the election video on November 14, 2026: another topic in
the friction cartoon's style, with cleaner professional-looking animation and
the approved 3D sample's captions. Topic: angular momentum on a swivel chair.

The visual direction, everyday setup → reversal → mechanism structure, isolated
renderer, narration/alignment pipeline and shared caption component come from
the friction/voxel experiments. Codex authored a new vector character/room and
connected arm rig rather than repurposing falling/slipping poses. Stock narrator:
Charlie via ElevenLabs. No Claude/Astra calls, copied source video or new service.

## Motion and fact model

`src/Motion.mjs` computes a smooth radial pose and integrates angular velocity
at 240 Hz. The rendered image samples that trajectory at 30 fps. It does not
reset the rotation each shot. The only deliberate reset is the spoken rewind
before the overhead replay. The chair base remains stationary; the seat, torso,
hands and weights rotate together. Fixed-length elbow solutions keep props
attached during extension/tucking. The selected elbow branch stays outside the
torso so the arms do not cross awkwardly through the head.

The demonstrative inertia is `I = 1 + 2(r² + 0.01)`: fixed body/chair inertia plus
two point masses. Tucking halves total I, so omega doubles at constant L. This is
an illustrative normalized system, not measured human limb masses or biomechanics.
The opening push supplies torque, the middle omits small bearing losses, and the
floor-braking segment reduces L smoothly to zero. Arms extending after stopping
do not magically restart the chair. The numerical checks supplement visual review.

Facts reviewed against [OpenStax University Physics, conservation of angular
momentum](https://openstax.org/books/university-physics-volume-1/pages/11-3-conservation-of-angular-momentum)
and [Simon Fraser University's rotating stool demonstration](https://www.sfu.ca/physics/demos/demos-experiments/stool-weights-burnaby.html):
negligible external torque conserves L; inward mass lowers I and raises omega;
muscular work supplies additional rotational kinetic energy; floor friction
provides braking torque. Script/illustrations are original, not reproduced textbook
prose or figures. The scope is axial rotation, not arbitrary rigid-body motion.

## Shot review

Ten beats: push/tuck hook → explicit overhead rewind → feet lifted/low torque →
inward motion → faster spin → outward slowdown → quantitative half-I/double-omega
example → muscular work/energy → floor braking → settled return to the room.
Inspect beginning, midpoint and ending for each, then full continuous playback.
The same white single-word captions sit below the action. Only useful equations,
relative values and diagram labels supplement them.

```sh
PYTHONPATH=services/api services/api/.venv/bin/python services/renderer/experiments/spin-story/prepare.py
python3 services/renderer/experiments/spin-story/sound.py
python3 services/renderer/experiments/spin-story/run.py stills
python3 services/renderer/experiments/spin-story/run.py video
python3 services/renderer/experiments/spin-story/finalize.py
python3 services/renderer/experiments/spin-story/verify.py
node --test services/renderer/tests/template-trials.test.mjs
```

Output: `.local/spin-story/output/spinning-chair/lesson.mp4`. Non-root/read-only,
offline Docker rendering has no provider credentials and bounded resources.
This authored local trial is not production integration or a claim of user
creative approval. Existing unrelated animations were not silently rerendered.
