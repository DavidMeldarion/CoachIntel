<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# CoachIntel Monorepo – Copilot Instructions (Universal React)

## Overview
- This monorepo hosts a SaaS with:
  - **Web app**: Next.js (App Router, SSR/SEO) rendering **React Native components via `react-native-web`**.
  - **Mobile app**: Expo (React Native) for iOS/Android.
  - **Backend**: FastAPI + Celery + Redis (Dockerized).
- **Primary languages**: TypeScript (apps + shared packages), Python (backend).
- **Package manager**: `pnpm`. **Monorepo**: Turborepo.
- **Goal**: **Maximize code reuse** across web and mobile. Write UI with **React Native primitives** and share domain logic, API clients, state, and most screens.

---

## Directory structure (authoritative)
```
.
├─ apps/
│  ├─ web/                # Next.js app (SSR/SEO) using react-native-web
│  └─ mobile/             # Expo app (React Native)
├─ packages/
│  ├─ ui/                 # Cross-platform RN UI library (Buttons, Inputs, Lists, etc.)
│  ├─ core/               # Types, constants, utilities, feature flags
│  ├─ validation/         # Zod schemas (source of truth for request/response/domain)
│  ├─ api/                # Generated TS client from FastAPI OpenAPI + TanStack Query hooks
│  ├─ auth/               # Cross-platform auth facade (web: NextAuth; mobile: PKCE + Keychain)
│  └─ platform/           # Small adapters (Link, FilePicker, Storage, VirtualList, Notifications)
├─ backend/               # FastAPI app + Celery worker
├─ infra/                 # Docker, docker-compose, IaC, local dev tooling
├─ .env.example
└─ turbo.json
```

> **Migration note**: Replace your old `/frontend` with `apps/web`. Keep `backend/` as-is, but expose OpenAPI for codegen.

---

## Universal React rules (for Copilot)
**Always**
- Import UI primitives from **`react-native`** (`View`, `Text`, `Pressable`, `FlatList`, `TextInput`, `Image`).
- Style with **Tamagui** or **NativeWind** (Tailwind-like) in `packages/ui`—not raw CSS classes.
- Render the same components on web via **`react-native-web`**.
- Put reusable UI in **`packages/ui`**; screens should be composable and platform-agnostic.
- Data fetching via **TanStack Query** + generated API client from **OpenAPI**.

**Never**
- Use DOM tags (`div`, `span`, `button`) **inside shared code**. DOM elements are allowed **only** in `apps/web` when absolutely necessary (marketing/SEO pages).
- Use browser-only APIs in shared code (`window`, `document`, `localStorage`, `navigator`). Use **`packages/platform`** adapters.
- Hardcode routing libraries in shared screens. Inject navigation with thin wrappers (Next.js App Router in web, Expo Router in mobile).

---

## Tech choices & constraints

### Web (apps/web)
- **Next.js (App Router)**, SSR/SEO enabled.
- Configure **react-native-web** + **Tamagui/NativeWind** in Next.js webpack/babel.
- Marketing pages may use DOM + shadcn/ui—but app surfaces should use RN components from `packages/ui`.

### Mobile (apps/mobile)
- **Expo** (managed workflow), **Expo Router**.
- **Auth**: OAuth2 **PKCE** via `expo-auth-session` (system browser) and **SecureStore** for refresh tokens.
- Push via `expo-notifications`; deep links via Universal Links.

### Shared data & validation
- **`packages/validation`**: **Zod** schemas = source of truth.
- **`packages/api`**: OpenAPI-generated TS client (e.g., `orval` or `openapi-typescript`), wrapped with TanStack Query hooks (`useQuery`, `useMutation`).

### Styling (pick one and stay consistent)
- **Tamagui** (preferred for compile-time optimizations, variants) **or**
- **NativeWind** (Tailwind-like for RN).  
Copilot should not generate raw CSS files or styled-components in shared UI.

---

## Platform adapters (packages/platform)
Create thin adapters to keep shared code platform-agnostic:

- `Link`: wraps Next.js `Link` (web) and Expo Router `Link` (mobile).
- `FilePicker`: `<input type=file>` (web) vs. ImagePicker/DocumentPicker (mobile).
- `Storage`: cookies/`localStorage` (web) vs. **MMKV/SecureStore** (mobile).
- `VirtualList`: react-window (web) vs. FlashList/FlatList (mobile).
- `Notifications`: Web Push (web) vs. APNs/Expo (mobile).
- `AuthUi`: buttons/providers that differ by platform (e.g., Apple Sign-In on iOS).

Each adapter exports a uniform interface; platform implementations live in `*.web.ts` / `*.native.ts`.

---

## Auth model (packages/auth)
- **Web**: NextAuth with HttpOnly cookie sessions. No token exposure to JS.
- **Mobile**: OAuth2 **PKCE** using system browser (`ASWebAuthenticationSession`), short-lived access tokens, refresh token in **Keychain**.
- Provide a shared facade:
  ```ts
  export type Session = { userId: string; roles: string[]; accessToken?: string };
  export function getSession(): Promise<Session | null>;
  export function signIn(provider?: 'google'|'apple'|'email'): Promise<void>;
  export function signOut(): Promise<void>;
  export function getAccessToken(): Promise<string | null>;
  export function onAuthStateChange(cb: (s: Session|null) => void): () => void;
  ```
- **Do not** store long-lived secrets in `localStorage` or a WebView. Use cookies (web) and **Keychain** (mobile).

---

## API codegen (packages/api)
- Backend exposes OpenAPI at `/openapi.json`.
- Script (root `package.json`):
  ```json
  {
    "scripts": {
      "codegen:api": "orval --config infra/orval.config.ts",
      "typecheck": "turbo run typecheck",
      "build": "turbo run build",
      "dev": "turbo run dev"
    }
  }
  ```
- Wrap generated clients with TanStack Query hooks and re-export typed hooks: `useListClients`, `useBrief(id)`, etc.

---

## Example component patterns

**Shared Button (packages/ui/src/Button.tsx)**  
```tsx
import { Pressable, Text } from 'react-native';
import { styled } from 'tamagui'; // or className with NativeWind

type Props = { title: string; onPress?: () => void; disabled?: boolean; testID?: string };
export function Button({ title, onPress, disabled, testID }: Props) {
  return (
    <Pressable accessibilityRole="button" disabled={disabled} onPress={onPress} testID={testID}>
      <Text>{title}</Text>
    </Pressable>
  );
}
```

**Platform Link adapter (packages/platform/link)**
```tsx
// link.web.tsx
'use client';
import NextLink from 'next/link';
export function Link(props: { href: string; children: React.ReactNode }) {
  return <NextLink href={props.href}>{props.children}</NextLink>;
}

// link.native.tsx
import { Link as ExpoLink } from 'expo-router';
export function Link(props: { href: string; children: React.ReactNode }) {
  return <ExpoLink href={props.href as any}>{props.children}</ExpoLink>;
}
```

**Shared screen using adapters (packages/ui/src/screens/Brief.tsx)**
```tsx
import { View, Text } from 'react-native';
import { Link } from '@coachintel/platform/link';
import { useBrief } from '@coachintel/api/briefs';

export function BriefScreen({ id }: { id: string }) {
  const { data, isLoading } = useBrief(id);
  if (isLoading) return <Text>Loading…</Text>;
  if (!data) return <Text>Not found</Text>;
  return (
    <View>
      <Text>{data.title}</Text>
      <Text>{data.summary}</Text>
      <Link href="/briefs">Back</Link>
    </View>
  );
}
```

---

## Backend (FastAPI + Celery + Redis)
- Keep FastAPI, Celery worker, and Redis **Dockerized**.
- Enable CORS for web/mobile origins.
- Expose **OpenAPI** and keep schemas accurate (drive codegen).
- Use **versioned** endpoints (`/v1`) with backward-compatible changes.

---

## Local development (Docker + scripts)
- `docker-compose` services: `api`, `worker`, `redis`, `db`, plus optional `mailhog`.
- Web dev: `pnpm --filter @coachintel/web dev` (Next.js).
- Mobile dev: `pnpm --filter @coachintel/mobile start` (Expo).
- Backend dev: `uvicorn app.main:app --reload`.
- One-shot bootstrap:
  ```bash
  pnpm i
  pnpm codegen:api
  docker compose up -d
  pnpm dev
  ```

---

## Environment configuration
- `.env` files per app: `apps/web/.env.local`, `apps/mobile/.env`, `backend/.env`.
- Never import environment variables directly in shared packages; pipe through app-level config and DI.
- Secrets: use platform-appropriate secure storage (Next.js runtime secrets, iOS Keychain).

---

## Testing & quality
- **Unit**: vitest/jest for TS packages; pytest for backend.
- **E2E web**: Playwright.
- **E2E mobile**: Detox (later).
- **Lint/format**: one ESLint + Prettier config at repo root; TS path aliases in `tsconfig.base.json`.
- **CI**:  
  - Web → Vercel (preview per PR).  
  - Mobile → EAS Build (internal distribution via TestFlight).  
  - Backend → Docker image build + deploy (your target).

---

## Copilot “Do / Don’t” checklist
**Do**
- Generate RN components in `packages/ui` using `View/Text/Pressable`.
- Use adapters from `packages/platform` for navigation, storage, files, notifications.
- Prefer **TanStack Query** for all data fetching; no ad-hoc `fetch` in components.
- Type everything; derive types from Zod/OpenAPI.
- Add platform forks with `*.web.tsx` / `*.native.tsx` only when necessary.

**Don’t**
- Suggest `div/span/button` in shared code.
- Use `window`, `document`, `localStorage` in shared code.
- Add CSS files or styled-components in shared code.
- Bypass the generated API client or Zod schemas.
- Handle OAuth entirely inside a WebView—use system browser (PKCE).

---

## Scaffolding targets (MVP)
- `packages/ui`: Button, Input, Card, List, Screen container, EmptyState, ErrorBoundary.
- `packages/platform`: Link, Storage, FilePicker, VirtualList, Notifications.
- `packages/validation`: zod schemas for User, Client, Brief, ActionItem, Auth tokens.
- `packages/api`: OpenAPI client + `useQuery`/`useMutation` hooks.
- `apps/web`: `/dashboard`, `/briefs/[id]` using shared screens.
- `apps/mobile`: `(tabs)/dashboard`, `(stack)/briefs/[id]` using shared screens.
- `backend`: endpoints for briefs list/detail, actions CRUD; Celery task example; OpenAPI aligned to zod.

---

## Definition of Done (per PR)
- Uses RN primitives and shared UI where feasible.
- No DOM or browser APIs in shared code.
- Types inferred from Zod/OpenAPI, no `any`.
- Tests updated; `pnpm typecheck && pnpm build` pass.
- Web builds (Vercel preview) and Mobile compiles (EAS/Expo local).

---

### One-line summary for Copilot
> **Build all app surfaces with React Native primitives, rendered on web via `react-native-web` and on mobile via Expo; keep domain logic, validation, and API clients in shared packages; use platform adapters for navigation/storage/files; reserve DOM/CSS for web-only marketing pages.**

