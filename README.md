# déclic

**A short-video feed that slips a study break into your scroll.** Built at **HackUMass 14**.

Students already spend time swiping through short videos. We built déclic around a simple question: could the next swipe help you understand something from class? déclic combines entertainment with short, captioned lessons and quick quizzes in an iPhone-first feed.

## What it does

- **Mixes Reels and lessons.** The personal feed starts with entertainment and introduces study clips as you watch. It balances courses, prioritizes upcoming assessments where available, and uses what you watched and answered to choose what to show next.
- **Turns Canvas material into micro-lessons.** A read-only Canvas connection imports accessible courses and materials. Background workers extract relevant concepts and create short visual explanations or narrated stories. The feed picks from ready clips, so swiping doesn't wait for a render.
- **Uses quizzes to pick a better explanation.** Submit an answer to continue, even if you get it wrong. A missed concept can come back with a different explanation when another clip is ready. Retries don't count twice.
- **Offers an optional demo library.** With an authenticated backend and a published demo catalog, you can try generic lessons without connecting Canvas. Our curated lineup used a tax bill to explain undo stacks, visualized JavaScript promise states, staged an inventory accounting problem in a shop, and told the story of the Wright brothers.

Getting video playback, signed media URLs, and quiz checkpoints to cooperate was a big part of the hack. The app buffers upcoming clips and keeps an issued quiz recoverable across a refresh. Our next steps are to quantify learning outcomes, improve course coverage, and make provider connections easier. The recommendation policy is rule-based; it hasn't been validated in a learning study.

## Try it without accounts or API keys

Use Node **24** (see [`.nvmrc`](.nvmrc)) and npm:

```sh
git clone https://github.com/agastyasandhuja/declic.git
cd declic
npm ci
cp apps/mobile/.env.example apps/mobile/.env
npm run web
```

Choose **Explore the demo** on the sign-in screen. This local development preview uses synthetic course data and publicly hosted test clips. It doesn't require a backend, and the clips need internet access. Use `npm run ios` for the iOS Simulator or follow the [mobile setup guide](apps/mobile/README.md) for Expo on iPhone.

For real sign-in, Canvas import, Instagram playback, generation, or the published demo library, follow [Run the integrated demo](docs/RUN_DEMO.md). Bring your own provider accounts and credentials. The hackathon's hosted catalog, private course files, provider sessions, and original video masters aren't part of this clone.

## How we built it

| Layer | What it does |
| --- | --- |
| **Expo · React Native · TypeScript** | Vertical feed, video playback, course setup, and quizzes |
| **FastAPI · Python · MongoDB Atlas** | Authenticated feed and quiz API, account-scoped application data, and durable job queues |
| **Supabase** | App authentication and private object storage for lesson media |
| **Canvas · Instagram** | Read-only course materials and an optional, account-connected entertainment catalog |
| **Gemini · Claude · ElevenLabs** | Course analysis and lesson planning, script and scene generation, and narration and timing |
| **Remotion · FFmpeg · Docker** | Isolated portrait video rendering and media checks |

Workers prepare lessons ahead of time. The API checks ownership before signing playable media URLs. Course-derived lessons are private by default; the shared demo uses a separate generic catalog. Generated scene code runs in a container without provider credentials or network access.

## Configuration and development

Start with the [root environment guide](.env.example). Copy the [mobile template](apps/mobile/.env.example) into `apps/mobile/.env` and the [API template](services/api/.env.example) into `services/api/.env` as needed. Keep server keys and Canvas or Instagram credentials out of `EXPO_PUBLIC_*` and Git. Use your own authorized Canvas and Instagram connections. Live provider access depends on institutional permissions, account checkpoints, and provider availability.

```sh
npm run typecheck
npm test
npm run contracts:check
(cd services/api && uv sync --locked && uv run --locked pytest -q)
npm --prefix services/renderer test
```

See the [API guide](services/api/README.md), [renderer guide](services/renderer/README.md), [data contracts](contracts/README.md), and [architecture notes](docs/PROJECT.md) for more detail. To set up the shared catalog with your own reviewed media, see the [publication workflow](contracts/demo-catalog.md).

Built by Adi (mobile, accounts, entertainment), Amogh (Canvas and curriculum), and Agastya (video generation, recommendations, quizzes, and integration).
