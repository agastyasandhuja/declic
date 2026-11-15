# Jensen's hypothetical GPU shop

Original procedural stylization: swept gray hair, square glasses and black leather
jacket. Charlie supplies ordinary third-person narration; there is no celebrity
voice imitation or claim that this shop/event is real. The opening says “Imagine”.
This separate trusted renderer cannot change the frozen 24-lesson renderer.

The source lesson and inherited accounting quizzes are in
`fixtures/learning/jensen-shop/lesson.json`. The physical sale moves one GPU from
shelf to Jensen's grip to the customer's grip; one cash prop enters the drawer
and remains there while COGS is recorded. The bookkeeper points at the now-empty
shelf, opens a physical ledger, and moves a cost marker while the second balanced
entry appears. The payoff is $40 gross profit before rent, not $100 cash proceeds.
The mistaken celebration is immediately challenged by the narrator/bookkeeper.

Shot review plan (beginning/action/end and continuous transitions):

1. Establish the small shop, buyer, Jensen and single GPU on its shelf.
2. Show the $60 shelf cost before sale; customer approaches the counter.
3. Customer deposits cash; Jensen reaches, carries and hands over the GPU;
   customer exits with that same object, Jensen raises his arm in celebration.
4. Bookkeeper's eyeline and pointing gesture lead back to the empty shelf.
5. Camera sees the physical ledger opening and the $100 Cash/Sales entry.
6. Bookkeeper moves the $60 cost marker across the open ledger; COGS/Inventory
   become the second entry. Inventory remains physically absent.
7. Ledger shows revenue100, COGS60 and gross profit40; drawer retains cash100.
8. Jensen lowers his victory pose; the scene settles rather than looping a wave.

The attached-prop and fixed-length-arm tests are geometric evidence, not visual
approval. Inspect grip/ownership transitions, face visibility, body collisions,
ledger legibility, caption occlusion and continuous motion in actual renders.
White single-word PopCaptions are reused unchanged. No overlay branding/headings.

Prepare with the API environment, approved script and existing Charlie voice:

```
python -m app.modules.videos.local_demo prepare --input fixtures/learning/jensen-shop/lesson.json --output /absolute/work --assets-root /absolute/repo --env-file /absolute/repo/.env --narrator-voice IKne3meq5aSn9XLyUdCD --workers 1
```

Run `run.py stills --id demo_acc233_perpetual --work /absolute/work --vendor
/absolute/three.module.js` only after coordinating the existing two render slots.
The same command with `video` is permitted after actual still review. The copied
bounded runner uses no network, credentials, extra image builds or host-render
fallback. Publication requires a separate exact-artifact review, the trusted
`jensen_shop` renderer profile, and the operator's work-directory override.

`node --test services/renderer/experiments/jensen-shop/test_story.mjs` tests custody,
fixed limb lengths and navigable customer exit. These tests do not synthesize
speech or render the experimental voxel scene.
