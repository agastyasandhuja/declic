# @hackumass/mobile-academics

Owner: Amogh. The academic feature UI (M5): Canvas connection, import progress,
course list, and course profile review/edit. **UI only** — it holds no secrets,
talks to no provider, and owns no navigation or auth. Adi mounts these at a route
he owns and injects the backend client, identity, and theme.

## Boundary (why there are no conflicts with Adi)

- No navigation container and no auth store live here (Adi owns both).
- No root `package.json`, workspace config, or lockfile is created here.
- Backend access is the injected `AcademicsApiClient`; identity and theme are props.
- `react` / `react-native` are peer dependencies, provided by the app.

## How Adi uses it

```tsx
import { AcademicsScreen } from '@hackumass/mobile-academics';
import { myRealApiClient } from '../lib/api'; // implements AcademicsApiClient

<AcademicsScreen api={myRealApiClient} identity={{ userId }} theme={appTheme} />
```

`myRealApiClient` must implement `AcademicsApiClient` (see `src/api/types.ts`),
mapping to the academic contract routes (`/v1/canvas/*`, `/v1/academics/*`).
A `FakeAcademicsApiClient` is exported for standalone use before the backend
endpoints exist.

## Exports

- `AcademicsScreen` — the composed screen (connection + progress + list + detail).
- `CanvasConnection`, `ImportProgress`, `CourseList`, `CourseProfile` — used alone too.
- `FakeAcademicsApiClient`, `defaultTheme`, and all contract types.

## What the UI guarantees

- Courses are ordered by **real-time urgency** (soonest real due date first).
- Dates are shown honestly: a date-only exam never shows an invented time; an
  unknown date reads "No date"; inferred/confirmed are labelled.
- Suggested practice is visually distinct from confirmed exam coverage.
- A student correction to an exam date is marked "you confirmed" and sent as a
  profile correction (new revision) — it never fabricates precision.

## Tests

Pure presentation logic (sorting, labels, date display, correction building) is
unit-tested and runs with Node's TypeScript support (no install needed):

```sh
npm test
# or: node --experimental-strip-types tests/format.test.ts
```

The React components are typed wrappers over that logic; they render once Adi's
Expo app hosts them (not runtime-verified in this package on their own).
