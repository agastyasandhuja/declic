# Ownership, integration, and acceptance

## Repository structure and file ownership

See the root README for the directory map and AGENTS.md for enforcement.
Use one modular API, one React Native app and one render worker. Individual domain
routers and workers can be tested alone against fakes.

| Shared surface | Single editor | How others contribute |
|---|---|---|
| Root JS workspace config and lockfile | Adi | Send package/version/import requirements |
| apps/mobile routes and app providers | Adi | Export components from feature packages |
| API main.py, core auth dependency, Python manifest | Agastya | Export router; request dependencies |
| Shared job table and dispatch | Agastya | Domain handler contract |
| Academic contract and source semantics | Amogh | Propose additions with example payload |
| Feed/quiz/render contracts | Agastya | Propose consumer requirements |
| Ordered database migrations | Agastya | Domain-owned draft files |

Every domain should have its own README with run instructions, a public interface,
synthetic fixtures, and meaningful tests. There is no root executable yet.
Pin dependencies and commit the corresponding lockfile when initializing runtimes.

## Bootstrap order

1. Adi initializes app/auth and JS workspace; Agastya initializes API/core/jobs.
2. Each owner writes domain schema definitions and synthetic fixtures from contracts.
3. Amogh and Agastya build their mobile feature packages only after agreeing on
   Adi's theme/API-client props; their backend work does not wait for this.
4. Adi plugs entertainment into the temporary feed endpoint.
5. Amogh publishes a multi-course profile/plan; Agastya consumes it through jobs.
6. Agastya publishes ready variants and unified feed; Adi swaps feed adapters.
7. All three verify the integrated scenario on the demo iPhone.

No teammate needs to wait for another's live API credentials to build their domain.
Fixtures are explicitly synthetic and must follow the same contracts as real data.

## Contract change protocol

The Markdown files in contracts are the initial v1 specification. Domain owners
implement runtime schemas under contracts/schemas/<domain> and examples under
fixtures/<domain>. No generated SDK/schema is claimed to exist yet.

Add optional fields compatibly. Renames, removed fields, new required fields and
changed semantics require producer/consumer coordination and a version change.
Record a decision in docs/decisions; Agastya reconciles shared protocol changes.
Consumers should tolerate unknown optional fields, but reject invalid required data.

Do not create a second definition of an ID, enum or timestamp in a neighboring
service. Python schemas and TypeScript types must derive from or validate against
the same versioned wire schema.

## Handoff artifacts

| Producer → consumer | Deliverable | Consumer can begin with |
|---|---|---|
| Adi → everyone | App identity, JWT verification adapter, current-user shape | Synthetic identity |
| Adi → Agastya | Entertainment adapter, normalized catalog, playback evidence | Fixture clips |
| Amogh → Agastya | AcademicProfile + LessonPlan + scoped source resolver | Three-course JSON fixture |
| Agastya → renderer | Validated RenderJob with local asset manifest | Generic lesson fixture |
| Renderer → Agastya | Asset references, duration, captions, QC results | Prepared MP4 metadata |
| Agastya → Adi | Unified feed, quiz submit and event routes | Mixed feed fixture |
| Amogh → Adi | Academic feature components | Fake API client |
| Agastya → Adi | Quiz feature component | Fake grading callback |

## Definition of done by milestone

### A. Entertainment-only app

Real iPhone: signup/login, persistent session, swipe video playback, one audio
source, background pause, recoverable provider failure. No Canvas required.

### B. Academic ingestion

All accessible current courses inventoried; source-backed profiles; explicit
missing dates; partial failures; balanced planned objectives; credentials private.

### C. Generation

Two formats for a common objective; narration/captions synchronized; 30–60 seconds;
rendered files inspected; ready assets reused without duplicate generation.

### D. Adaptive mixed feed

Study share increases during active session; multiple courses appear; quiz locks
swiping until valid answer; wrong answer unlocks and changes future unseen ranking;
alternate explanation appears after intervening content.

### E. Demo readiness

Document live/cached/fixture sources, backend reachability from iPhone, prepared
media, provider outage fallback, and exact commands. A UI screenshot alone does
not verify authentication or recommendation behavior.

## Local ports and environment ownership

Proposed API: 8000. Internal renderer: 8001. Mobile origin is reachable from the
phone and must not be localhost on the phone. Long-lived secrets are server-only.

| Variable family | Owner | Location |
|---|---|---|
| EXPO_PUBLIC_API_BASE_URL, public Supabase URL/key | Adi | Mobile public config |
| Supabase server/database credentials | Agastya | Backend secret environment |
| Canvas domain, OAuth key/secret, local demo token | Amogh | Backend secrets; token bound to test user |
| GEMINI_API_KEY, GEMINI_MODEL | Amogh | Curriculum worker |
| ANTHROPIC_API_KEY, CLAUDE_MODEL | Agastya | Generation worker |
| ELEVENLABS_API_KEY, speaker voice IDs | Agastya | Generation worker |
| TikTok/Instagram session material | Adi | Entertainment worker secrets |
| Renderer runtime config | Agastya | Renderer; no provider keys |

Owners add exact .env.example files with placeholders when implementation begins.
Never put service-role keys in EXPO_PUBLIC variables.

## Database workflow

Domain owners prepare changes in database/domains/<domain>. Agastya assembles
ordered migrations in database/migrations and records dependencies. Do not have
three agents alter one initial-schema SQL file. Use current CLI guidance when
generating actual migration files; no executable migrations exist in this scaffold.

## Updates

Each owner updates only their docs/status file, recording completed work,
commands/results, interface changes, dependencies, and remaining work.
Avoid blanket “done” claims when provider/device verification is still pending.
