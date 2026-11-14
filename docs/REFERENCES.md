# Research references and verification boundaries

Reviewed November 13, 2026. These support the architectural choices; documentation
and source inspection are not live integration tests. Recheck exact methods and
SDK versions during implementation. Product requirements come from the user.

## Entertainment

- [TikTok-Api repository](https://github.com/davidteather/TikTok-Api):
  unofficial Python client; browser-session setup and trending example.
- [Trending implementation](https://github.com/davidteather/TikTok-Api/blob/main/TikTokApi/api/trending.py):
  recommendation-list endpoint; personal native-app FYP fidelity remains unverified.
- [instagrapi](https://github.com/subzeroid/instagrapi):
  unofficial Instagram client; account/session challenges are an integration risk.
- [Media methods](https://github.com/subzeroid/instagrapi/blob/master/docs/usage-guide/media.md):
  creator clips, media information and download helpers.
- [TikTok embed player](https://developers.tiktok.com/docs/en/embed-player):
  curated clip playback alternative; device autoplay behavior still needs testing.
- [TikTok Display API](https://developers.tiktok.com/docs/en/display-api-overview):
  creator/profile video display; not a documented personalized FYP API.

## Canvas

- [Canvas API resources](https://developerdocs.instructure.com/services/canvas):
  implementation reference for current endpoint schemas.
- [Courses](https://developerdocs.instructure.com/services/canvas/resources/courses):
  course discovery and syllabus data.
- [OAuth overview](https://developerdocs.instructure.com/services/canvas/oauth2/file.oauth):
  institution-issued developer credentials and server token exchange.
- [Developer keys](https://www.canvas.instructure.com/doc/api/file.developer_keys.html):
  institution enablement and scoped access.

A developer's own local test token is a demo development fallback. A multi-user
Canvas connection should use OAuth. Calendar completeness, access to files and
external course tools depend on institution and student permissions.

## Models, video and storage

- [Gemini document understanding](https://ai.google.dev/gemini-api/docs/document-processing):
  supports reading document content including visual PDF information.
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output):
  schema-shaped extraction; facts still require validation.
- [Remotion](https://www.remotion.dev/) and [agent guidance](https://www.remotion.dev/docs/ai/skills):
  programmatic React-based video and coding-agent workflows.
- [ElevenLabs timed speech](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps):
  audio with alignment useful for synchronized narration and captions.
- [Supabase React Native auth](https://supabase.com/docs/guides/auth/quickstarts/react-native):
  proposed managed identity implementation.
- [Supabase changelog](https://supabase.com/changelog):
  verify current CLI and SDK behavior before creating resources/migrations.
- [Supabase Storage buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals):
  private document/media storage and signed access; retained with Atlas.
- [MongoDB data modeling](https://www.mongodb.com/docs/manual/data-modeling/):
  adopted application datastore; domain owners draft collection shapes.
- [MongoDB schema validation](https://www.mongodb.com/docs/manual/core/schema-validation/specify-json-schema/):
  collection validation; runtime API schemas remain governed by the contracts.
- [MongoDB indexes](https://www.mongodb.com/docs/manual/reference/method/db.collection.createindex/)
  and [transactions](https://www.mongodb.com/docs/manual/core/transactions/):
  uniqueness and atomic domain/outbox changes; implementation remains untested.
- [MongoDB Vector Search](https://www.mongodb.com/docs/vector-search/query/aggregation-stages/vector-search-stage/):
  optional later lesson discovery; not required for the first mobile milestone.

Model IDs, voice IDs, generated-code isolation implementation, performance and
costs have not been validated by this planning scaffold.

## Nearby products

- [LearnScroll](https://learnscroll.app/): advertises course-material study videos.
- [Brainjuice](https://brainjuice.app/): advertises a swipeable educational feed.
- [ScrollScholar](https://scrollscholar.com/): course questions to earn screen time.

These are product descriptions, not independently verified feature tests.
Our intended distinction is entertainment mixed with course-timed lessons and
feedback-driven reteaching on a phone; do not claim the whole category is new.
