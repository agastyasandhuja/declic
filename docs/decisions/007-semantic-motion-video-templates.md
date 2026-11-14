# 007 — Semantic motion and minimal video templates

Date: 2026-11-14. Accepted direction at the user's request; local implementation
and validation are in progress. This decision records interfaces and design
intent, not completed render results, publication or mobile playback.

The user rejected decorative stock photographs, repeated spatial animation,
small mathematical objects and excessive on-screen text. The next batch uses
different topics in psychology, personal finance, biology and geometry. Earlier
linked-list, matrix and space lessons remain supported historical examples.

Keep the Python generation harness and isolated Remotion renderer. No replacement
stack, extra service or new mobile format identifier is needed. The video-specific
model remains `VIDEO_CLAUDE_MODEL=claude-opus-5-5` by default, independently of the
generic model setting. Model-produced plans are untrusted; trusted code computes
quantities and geometry, and validators reject unsupported input.

## Additive internal interfaces

Public VideoVariant, feed and MP4 playback fields keep their existing names.
`schema_version` remains `"1"`. New fields have defaults so existing briefs and
storyboards remain readable by the updated worker. New plans require the matching
updated renderer/validator; older strict internal validators are not expected to
accept them. Template/source fingerprints distinguish new generation from cached
historical artifacts.

| Internal field | Meaning and bounds |
| --- | --- |
| `Brief.math_topic` | `matrix_multiplication` by default, or `pythagorean_rearrangement`; only math lessons use the alternative. |
| `Brief.pythagorean_sides` | Exactly two strict integers in 1…9, representing positive perpendicular sides. Required for Pythagorean math; incompatible with matrix inputs. |
| `Brief.installment_example` | Optional `{unit_price, installments, purchases}` for `visual_explainer` with `trace_kind=none`. Strict integer bounds: unit price 4…10000, installments 2…4, purchases 1…3. Unit price must divide evenly by installments. |
| `Shot.motion_scene` | Defaults to `none`. Non-`none` modes require `kind=diagram`. Names select authored geometry, not arbitrary executable code. |
| `Shot.space_mode` | Retains existing modes and adds the `enzyme_*` modes below under the existing `space_explainer` identifier. |

Payment modes: `price_tag`, `split_payment`, `stack_purchases`,
`payment_calendar`, `total_cost`, `choice_balance`, `receipt`. They require the
validated installment example. Values such as each payment, the combined payment,
the total commitment and the remaining balance are derived from those inputs.
The example is explicitly hypothetical; the renderer does not invent lender
terms, rates or dates. A semantic payment plan uses authored objects and exact
numbers instead of requiring four stock photographs. Historical photo plans
continue through their existing asset-selection and review path.

Decision modes: `ticket_purchase`, `ticket_loss`, `future_choice`, `time_loss`,
`decision_reset`. These depict the bounded $20 nonrefundable movie-ticket example
with one hour remaining. They are an authored example, not a generic simulation
for arbitrary amounts or decisions. The ticket remains irrecoverable under both
choices; the future hour is compared separately. The explanation must not imply
that ignoring sunk costs means always quitting.

Biology modes: `enzyme_hook`, `enzyme_fit`, `enzyme_reaction`, `enzyme_reuse`,
`enzyme_compete`, `enzyme_concentration`, `enzyme_denature`. These are illustrative
mechanism scenes, not measured molecular structures or scientific simulations.
All-enzyme storyboards do not need unrelated NASA assets. Existing astronomical
modes and image-backed space storyboards retain their supported path. Four
distinct demonstrations and no immediately repeated spatial mode remain the
reference-v3 diversity baseline; different camera moves alone are insufficient.

Pythagorean math uses four congruent right triangles and two exact endpoint
arrangements inside the same square. Trusted calculations provide side lengths,
triangle area, outer area and square areas; the renderer verifies the plan.
Animated intermediate positions are transitions, not additional proof states.
The final area relationship is `a² + b² = c²`. Existing compatible 2–3-row/column
matrix inputs and the original dot-product path remain supported. Music-led math
keeps the 20–60-second range; narrated lessons keep 30–60 seconds.

## Presentation and review policy

- Dialogue uses original, concept-related Stewie snark and short exchanges.
  Diagrams have transparent backgrounds and readable object outlines/shadows.
  Gameplay is muted; narration is the only soundtrack. No music is added.
- Payment stories show the actual quantity change: split, accumulate, schedule,
  reconcile. A small first payment must not visually masquerade as the total price.
- Narrated animation uses short yellow captions with restrained synchronized
  bounce. Remove redundant headings, prose and source footers; essential object
  labels remain allowed. Distinct movement must explain distinct claims.
- Math uses a black canvas, large geometric/mathematical objects, consistent accent
  colors and movement that demonstrates the relation. No narrated captions or
  explanatory prose is required. A written hook is not a prerequisite when the
  opening visual already establishes the question.
- Sources and required asset/music attribution accompany the artifact in metadata
  and `CREDITS.txt`. A future sharing/publishing integration must carry these into
  the description or accompanying attribution; removing the footer does not remove
  the attribution requirement.
- Source review, exact-value checks, sampled-frame review and final media checks
  are distinct gates. Frame review must respect the user's minimal style and report
  timestamped defects separately from optional taste notes. Sampled frames cannot
  establish smooth motion, natural audio delivery or joke quality.

## Source basis and integration consequences

The finance example uses the CFPB's description of
[BNPL installment borrowing](https://www.consumerfinance.gov/ask-cfpb/what-is-a-buy-now-pay-later-bnpl-loan-en-2119/)
and its explanation that [fees and terms vary](https://www.consumerfinance.gov/ask-cfpb/do-buy-now-pay-later-bnpl-loans-have-fees-en-2118/).
The $100/four-payment/three-purchase scenario is our arithmetic example, assumes
no interest or fees, and is not advice to borrow or a claim about every provider.
No claim about current legal protections or exact market rates is needed.

The psychology example is grounded in
[Arkes and Blumer, *The Psychology of Sunk Cost* (1985)](https://cognition.aau.at/bg/BA/Arkes%20%26%20Blumer%201985.pdf),
especially its distinction between irrecoverable past spending and expected future
costs/benefits. The specific movie dialogue and dollar amount are original
hypothetical teaching material, not reported experimental observations.

Creator workflows and the limits of their evidence are documented in
[AI short-form creator research](../AI_SHORT_FORM_CREATOR_RESEARCH.md). Neither
that research nor a successful local render establishes better learning, attention
or virality for this implementation.

Adi may optionally display `space_explainer` as **Animated science**. This is a
display-label coordination request, not an enum rename or a mobile navigation edit.
Curriculum can continue proposing the existing format IDs; Agastya's generation
layer chooses only supported subject/mode combinations. No database migration,
authentication change or mobile playback payload change is required. Keep generated
MP4s and local diagnostics out of Git. Actual checks, exports and remaining limits
are recorded separately in `docs/status/AGASTYA.md`.

## Cost control and editable scripts

Claude outputs are cached per work directory using the exact model, system prompt,
schema, payload and attached image bytes. Cache hits are validated again, recorded
as `cache_hit`, and do not call or charge the provider. A changed brief, frame,
prompt or schema causes a cache miss. Cached failures are not promoted to passes;
malformed cached data fails closed. Fact review always goes through this cache,
so matching fact IDs alone cannot reuse an approval after their statements change.

`generate --storyboard-file PATH` accepts a locally edited, schema-validated script.
It retains the live factual and rendered-frame gates, marks its editorial origin,
and is distinct from `--fixture`. This avoids paying to regenerate an entire script
for a small correction. Per-segment voice caches retain matching audio/alignment.
The fixed 1.08× dialogue and 1.12× semantic-narration tempos remap timestamps and
are independently tested against actual ffmpeg output. Semantic shots exceeding
eight measured seconds trigger bounded script repair, not an automatic speed increase.

The frame reviewer identifies `repair_scope`: script/scene selection can use a
bounded storyboard repair; an authored geometry defect stops for implementation
repair instead of spending tokens rewording speech. The local `render` command
requires a current passing review for a live pack. Publication remains separate
and requires its existing human review.

The follow-up research also led to local motion-inspection exports. After a full
render, `motion_review.py` creates short audio/video clips and six-frame strips at
openings, transitions, the longest shot, meaningful internal cycles/rearrangements,
and the payoff. The clip index binds to the source MP4 SHA-256. Matching outputs
reuse their cache without re-encoding. These artifacts use no model calls and make
mid-motion inspection practical; their existence is not an automatic visual pass
or a substitute for listening and watching the complete lesson.
