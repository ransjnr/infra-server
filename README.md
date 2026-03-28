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

## Deploy on Render

This repo includes a **[Render Blueprint](https://render.com/docs/infrastructure-as-code)** at [`render.yaml`](render.yaml): **Postgres**, **Key Value (Redis‑compatible)**, four **Docker web services** (dataset-manager, intelligence, speech, gateway), and wired env vars (`DATABASE_URL`, `REDIS_URL`, upstream `https://…onrender.com` URLs, generated `JWT_SECRET`).

### Steps

1. **Push** this `infra-server` tree to GitHub/GitLab/Bitbucket (or ensure Render can see it). If your Git **root is a parent folder** that only *contains* `infra-server`, either open a repo that uses `infra-server` as the root or, in Render, set **Root Directory** to `infra-server` for **each** web service and keep paths as in `render.yaml`.
2. In the [Render Dashboard](https://dashboard.render.com/), choose **New → Blueprint**, connect the repo, and point Render at **`render.yaml`** (at the repo root for that service, usually the same folder as `docker-compose.yml`).
3. Apply the Blueprint. When prompted, set **sync: false** secrets:
   - **`GHANA_NLP_API_KEY`** (intelligence + speech)
   - **`CORS_ORIGINS`** — your production frontend origin(s), comma‑separated (no spaces), e.g. `https://myapp.vercel.app`
   - **`PUBLIC_BASE_URL`** — set to the gateway’s public URL once you know it (see below).
4. Wait for all services to go **Live**. Postgres and the internal Redis URL are injected automatically; web apps listen on Render’s **`PORT`** (handled in the Dockerfiles).
5. **Swagger host:** copy the **infra-gateway** service URL (`https://…onrender.com`, same as `RENDER_EXTERNAL_URL` in the dashboard) into **`PUBLIC_BASE_URL`** for **infra-gateway** (Environment → add or edit `PUBLIC_BASE_URL`), then **Manual Deploy** that service so `/docs` “Try it out” calls the correct HTTPS host.
6. **Smoke test:** `GET https://<gateway>/health`, open `https://<gateway>/docs`, **register** / **login**, then call a proxied route with **Authorize**.

### Operational notes

- **Cost:** the Blueprint includes a **paid** Postgres plan (`basic-256mb` in `render.yaml`); adjust `plan` to match your workspace. Web services use the **free** instance type by default — they **spin down** when idle (cold starts, slow first request).
- **Memory:** **intelligence** (PyTorch + Transformers) and **speech** (Whisper) often need more RAM than a free web instance provides. If builds succeed but the container crashes on startup, upgrade **infra-intelligence** and **infra-speech** to a paid instance type in the dashboard.
- **Ephemeral disk:** model weights download to the container filesystem; they are **re-fetched after redeploys** unless you add a [persistent disk](https://render.com/docs/disks) and point caches there (not configured in this Blueprint).
- **Security:** treat **8001–8003** backends as internal only; your public API should be **infra-gateway**. Restrict CORS to real frontend origins in production.

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
