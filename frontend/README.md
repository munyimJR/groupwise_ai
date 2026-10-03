# GroupWise AI — web app

Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui (Base UI).
See the [root README](../README.md) for the product, architecture and setup.

```bash
cp .env.example .env.local   # set BACKEND_URL (FastAPI) and optional Supabase public keys
npm install
npm run dev                  # http://localhost:3000
```

The browser calls `/api/*` on this origin; `next.config.ts` proxies it to `BACKEND_URL`.
