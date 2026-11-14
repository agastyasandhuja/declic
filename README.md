# HackUMass XIV — Study in your feed

An iPhone-first React Native app that mixes short-form entertainment with
30–60 second lessons generated from a student's Canvas courses. Course schedules,
upcoming exams, and quiz answers guide the study recommendations.

**Current status:** architecture, ownership guides, and directory scaffold only.
There is no runnable app or configured cloud infrastructure yet. Technology
choices below include the adopted MongoDB Atlas database decision; remaining
defaults and user-confirmed product requirements are identified in the project
document.

## Start here

1. Read [AGENTS.md](AGENTS.md) for ownership and collaboration rules.
2. Read [the project and architecture document](docs/PROJECT.md).
3. Read [the shared integration contracts](contracts/README.md).
4. Follow your assignment:
   - [Adi — mobile app, authentication, entertainment](docs/tasks/ADI.md)
   - [Amogh — Canvas and Gemini curriculum preprocessing](docs/tasks/AMOGH.md)
   - [Agastya — video generation, quizzes, recommendations](docs/tasks/AGASTYA.md)
5. Use [integration milestones](docs/INTEGRATION.md) for handoffs and demo checks.

## Stack

| Layer | Default |
|---|---|
| iPhone UI | React Native + Expo + TypeScript |
| App identity | Supabase Auth |
| Application database | MongoDB Atlas |
| Documents and media files | Supabase Storage |
| HTTP API and domain logic | Python + FastAPI, one modular backend |
| Entertainment adapters | TikTok-Api first experiment; instagrapi alternative |
| Course extraction and lesson planning | Gemini, with validated structured output |
| Video writing and scene generation | Claude |
| Narration and alignment | ElevenLabs |
| Compositing | Remotion + React/SVG + FFmpeg |
| Background work | Persistent Atlas jobs collection + separate workers initially |

Atlas replaces the proposed Postgres application tables for profiles, courses,
lesson plans, video metadata, jobs, quizzes and feed state. Supabase continues to
handle accounts and file storage. The phone accesses Atlas-backed data through
the authenticated FastAPI API. See the [accepted decision](docs/decisions/001-proposed-atlas-application-data.md)
and [database ownership/setup plan](database/README.md). No Atlas cluster or
database connection has been provisioned or tested by this scaffold.

## Repository map

| Directory | Purpose | Owner |
|---|---|---|
| apps/mobile | App shell, navigation, auth, playback, feed UI | Adi |
| services/api/app/modules/auth | App identity adapter | Adi |
| services/api/app/modules/entertainment | Entertainment catalog and provider adapters | Adi |
| services/api/app/modules/canvas | Canvas connection and ingestion | Amogh |
| services/api/app/modules/curriculum | Gemini profiles and lesson plans | Amogh |
| services/api/app/modules/{videos,recommendations,quizzes} | Learning runtime | Agastya |
| services/api/app/core | API assembly, auth dependency, configuration, job primitives | Agastya |
| services/renderer | Isolated Node/Remotion render worker | Agastya |
| packages/mobile-academics | Course connection/profile feature components | Amogh |
| packages/mobile-learning | Quiz/progress feature components | Agastya |
| contracts | Domain interface definitions; see ownership inside | Split by file |
| database | Domain collection/index drafts and ordered database changes | Split / Agastya integrates |
| fixtures | Synthetic, nonprivate integration samples | Split by subfolder |
| docs | Product architecture, integration, references, task guides | Split by document |

Empty implementation directories contain tracked .gitkeep files. Each owner
should replace them with implementation as work begins. Do not assume placeholder
directories contain generated application code.

## First deliverable

Adi's first milestone is **signup → login → scroll entertainment on a real iPhone**.
It has no Canvas dependency and does not require completed AI video generation.
Other streams work against the contracts and their own fixtures.

## Running the project

No run commands are available yet. As each service is initialized, its owner must
add exact install/run/test commands and environment variable names to its local
README. Do not commit real keys, tokens, Canvas files, or downloaded media.
