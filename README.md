# Infra

Infra is an AI data infrastructure monorepo: a FastAPI **gateway** (JWT auth + merged OpenAPI), **dataset-manager** (PostgreSQL + SQLAlchemy), **intelligence** (Khaya translation + sentiment), **speech** (Whisper + intelligence), plus **PostgreSQL** and **Redis**. User accounts live in PostgreSQL (`users` table); the gateway issues JWTs and protects `/api/*` (set `AUTH_ENABLED=false` only for local debugging).

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/) v2+
- Enough disk and RAM for first-time model downloads (Whisper, Hugging Face, etc.)

## Environment variables

Compose substitutes `${VAR}` values from:

1. Your **shell** environment, and  
2. A **`.env` file** in the **same directory as `docker-compose.yml`** (the project root).

Copy the template and edit:

```bash
cp .env.example .env
```

Set at least:

| Variable | Purpose |
|----------|---------|
| `GHANA_NLP_API_KEY` | Required for **intelligence** `/analyze` and **speech** (after transcription). Get a key from [Khaya / Ghana NLP](https://translation.ghananlp.org/). |
| `DATABASE_URL` | Default inside Compose is `postgresql://infra:infra@postgres:5432/infra` — usually fine as-is for local Docker. |
| `JWT_SECRET` | Signing key for gateway JWTs; set a strong random value in any shared or production environment. |
| `AUTH_ENABLED` | Default `true`. When `true`, `/api/*` on the gateway requires `Authorization: Bearer <token>`. |

Optional overrides (see `.env.example`): `CORS_ORIGINS`, upstream URLs, ports, Postgres credentials.

## API docs (Swagger) and authentication

- Open **`http://localhost:8000/docs`** (or your `GATEWAY_PORT`) for a **single** Swagger UI that lists gateway **authentication** routes and **merged** paths for dataset-manager, intelligence, and speech (tagged as “proxied”). Use **Authorize** and paste a JWT from `POST /auth/login`.
- Register: `POST /auth/register` with JSON `{"email":"you@example.com","password":"yourpassword"}` (minimum 8 characters).
- Token: `POST /auth/login` returns `access_token`; send `Authorization: Bearer <access_token>` on `/api/...` requests.
- Direct access to ports **8001–8003** does not go through gateway auth; use the gateway in production-style setups.

## Project structure (`infra-server`)

```
infra-server/
├── docker-compose.yml          # Local stack: Postgres + Redis + 4 services
├── render.yaml                 # Render Blueprint (Supabase DB + Render Key Value + 4 web services)
├── .env.example                # Template for local `.env`
├── requirements.txt            # Optional combined local installs
├── shared/                     # Code shared by all Python services
│   ├── logging_utils.py
│   └── schemas.py
└── services/
    ├── gateway/                # JWT auth, reverse proxy, merged OpenAPI (/docs)
    ├── dataset-manager/        # Datasets API + SQLAlchemy models (`datasets` table)
    ├── intelligence/         # /analyze (Khaya + sentiment)
    └── speech/                 # /transcribe (Whisper → intelligence)
```

Each service has its own `Dockerfile`, `requirements.txt`, and `main.py`. Docker build **context** is the `infra-server` root so Dockerfiles can `COPY shared/…` and `COPY services/<name>/…`.

## Deploy on Render (with Supabase Postgres)

The Blueprint in [`render.yaml`](render.yaml) provisions **Render Key Value** (Redis‑compatible) and **four Docker web services**. **PostgreSQL is not created on Render** — use **[Supabase](https://supabase.com)** (free tier) or any hosted Postgres, then set **`DATABASE_URL`** on each web service.

### A. Create the database on Supabase

1. Sign in at [supabase.com](https://supabase.com) → **New project** (choose a region close to your Render region, e.g. US West).
2. Wait until the project is ready. Open **Project Settings → Database**.
3. Under **Connection string**, choose **URI** and copy the string. Prefer the **Session pooler** (or **Transaction pooler**) on port **6543** when four services connect to the same DB, so you do not hit the direct connection limit. Replace `[YOUR-PASSWORD]` with your database password.
4. Ensure the URI includes SSL, e.g. `?sslmode=require` at the end (Supabase often adds this in the copy‑paste string).
5. You do **not** need to create tables manually first: **dataset-manager** and **gateway** call SQLAlchemy `create_all` on startup for `datasets` and `users`.

### B. Apply the Render Blueprint

1. **Push** this repo so Render can clone it (Git root should be **`infra-server`**, or set **Root Directory** to `infra-server` for each Docker service if the repo root is higher).
2. In the [Render Dashboard](https://dashboard.render.com/) → **New → Blueprint** → connect the repo → select **`render.yaml`**.
3. When Render prompts for **`sync: false`** variables, provide:
   - **`DATABASE_URL`** — paste the **same** Supabase URI for **each** of the four web services when asked (dataset-manager, intelligence, speech, gateway each declare their own `DATABASE_URL`; identical value is correct).
   - **`GHANA_NLP_API_KEY`** — intelligence and speech (two prompts).
   - **`CORS_ORIGINS`** — e.g. `https://your-app.vercel.app` (comma‑separated, no spaces).
   - **`PUBLIC_BASE_URL`** — leave blank or placeholder for now; set after step 4.
4. Wait until **infra-redis** and all four web services are **Live**. **`REDIS_URL`**, upstream **`RENDER_EXTERNAL_URL`** links, and **`JWT_SECRET`** are applied by the Blueprint.

### C. Finish gateway URL and Swagger

1. Open the **infra-gateway** service → copy its **`https://….onrender.com`** URL.
2. **Environment** → set **`PUBLIC_BASE_URL`** to that exact URL (no trailing slash) → **Save** → **Manual Deploy** infra-gateway so `/docs` “Try it out” uses HTTPS.

### D. Smoke test

- `GET https://<gateway>/health`
- `https://<gateway>/docs` → register → login → **Authorize** → try a proxied route.

### Optional: fewer secret prompts

After the first deploy, you can create a Render [**Environment Group**](https://render.com/docs/configure-environment-variables#environment-groups) holding **`DATABASE_URL`** (and other shared secrets), attach it to all four web services, and remove duplicate `DATABASE_URL` entries from `render.yaml` on the next Blueprint sync (advanced).

### Operational notes

- **Cost:** no Render-managed Postgres in this Blueprint; Supabase free tier has its own limits. Render **Key Value** and **free web** instances may still require a card on file depending on your Render account policy.
- **Memory:** **intelligence** and **speech** may **OOM** on free Render RAM; upgrade those instance types if containers exit after boot.
- **Ephemeral disk:** models re-download after redeploy unless you add persistent disk / external cache.
- **Security:** use **infra-gateway** as the public API; keep **`CORS_ORIGINS`** tight in production.

## Start the full stack

From the **repository root** (where `docker-compose.yml` lives):

```bash
docker compose up --build
```

- First build can take a long time (PyTorch, Whisper, Transformers, model downloads on first request).
- Gateway listens on **8000** by default; backends on **8001–8003**.

Stop:

```bash
docker compose down
```

## Architecture (ports)

| Service | Container port | Host default | Role |
|---------|----------------|--------------|------|
| **gateway** | 8000 | 8000 | JWT auth (`/auth/*`), reverse proxy: `/api/datasets/*`, `/api/intelligence/*`, `/api/speech/*`, merged `/docs` |
| **dataset-manager** | 8001 | 8001 | Datasets API + Postgres |
| **intelligence** | 8002 | 8002 | Text analyze (Khaya + sentiment) |
| **speech** | 8003 | 8003 | Transcribe audio → calls intelligence |
| **postgres** | 5432 | 5432 | Database |
| **redis** | 6379 | 6379 | Cache / future use |

## Python dependencies

Each service under `services/*/requirements.txt` includes a shared **baseline**: `fastapi`, `uvicorn`, `sqlalchemy`, `httpx`, `psycopg2-binary`, `openai-whisper`, plus service-specific packages. A root **`requirements.txt`** lists the combined stack for optional local installs (install CPU PyTorch first; see comments in that file).

## Sample `curl` checks

Replace host ports if you changed `GATEWAY_PORT`, `DATASET_MANAGER_PORT`, etc.

### Gateway (entry point)

```bash
curl -sS http://localhost:8000/health
```

Proxied health (dataset-manager; requires a JWT when `AUTH_ENABLED=true`):

```bash
curl -sS http://localhost:8000/api/datasets/health \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Dataset-manager (direct)

```bash
curl -sS http://localhost:8001/health
```

Create a dataset (direct to service):

```bash
curl -sS -X POST http://localhost:8001/datasets/ \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Sample corpus\",\"language\":\"tw\",\"type\":\"text\",\"file_url\":\"https://example.com/data.jsonl\",\"metadata\":{\"description\":\"This description is longer than fifty characters for scoring.\",\"tags\":[\"proverb\"]}}"
```

Same path **through the gateway** (add `Authorization` when `AUTH_ENABLED=true`):

```bash
curl -sS -X POST http://localhost:8000/api/datasets/datasets/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Sample corpus\",\"language\":\"tw\",\"type\":\"text\",\"file_url\":\"https://example.com/data.jsonl\",\"metadata\":{\"description\":\"This description is longer than fifty characters for scoring.\",\"tags\":[\"proverb\"]}}"
```

### Intelligence

```bash
curl -sS http://localhost:8002/health
```

Analyze text (requires `GHANA_NLP_API_KEY` in `.env`):

```bash
curl -sS -X POST http://localhost:8002/analyze \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"I am fine, me ho yɛ paa charlie\"}"
```

Via gateway:

```bash
curl -sS -X POST http://localhost:8000/api/intelligence/analyze \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Hello from Infra\"}"
```

### Speech

```bash
curl -sS http://localhost:8003/health
```

Transcribe an audio file (requires a real `.wav` or `.mp3` path on your machine):

```bash
curl -sS -X POST http://localhost:8003/transcribe -F "file=@/path/to/sample.wav"
```

Via gateway:

```bash
curl -sS -X POST http://localhost:8000/api/speech/transcribe \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@/path/to/sample.wav"
```

Speech calls intelligence after transcription; ensure `GHANA_NLP_API_KEY` is set.

### PostgreSQL & Redis

These are not HTTP services. Quick checks from the host:

```bash
docker compose exec postgres pg_isready -U infra -d infra
docker compose exec redis redis-cli ping
```

## Troubleshooting

- **`502` / `503` on `/analyze` or `/transcribe`:** set `GHANA_NLP_API_KEY` in `.env` and recreate containers (`docker compose up --build`).
- **Gateway cannot reach backends:** ensure service names match `DATASET_MANAGER_URL`, `INTELLIGENCE_SERVICE_URL`, `SPEECH_SERVICE_URL` (defaults target Docker network hostnames).
- **CORS from Next.js:** set `CORS_ORIGINS` to your dev origin (e.g. `http://localhost:3000`). Use `CORS_ORIGINS=*` only for quick tests (credentials are disabled when `*`).
