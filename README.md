# JokeGen Backend

A small Flask + SQLite backend for serving jokes, search, and audio to a static frontend.

## Repository Structure

- `backend/` — Flask API and application files
  - `app.py` — main Flask application exposing the API
  - `requirements.txt` — Python dependencies
  - `requirements-dev.txt` — dependencies for running tests (includes `requirements.txt`)
  - `tests/` — pytest test suite
  - `Joke audio/` — committed directory of `joke*.mp3` files served by the app
- `Database/` — helper scripts for creating and populating the SQLite database
  - `db.py` — utilities to create `jokegen.db`, read `clean_base.txt`, and populate the DB
  - `clean_base.txt` — cleaned jokes source (plain text)
  - `clean_base.py` — one-off script that produces `clean_base.txt` from a raw `base.txt`

## Features

- Serve random jokes and search by text, with pagination
- Retrieve specific jokes by number
- Serve pre-recorded joke audio files from `backend/Joke audio`, with caching headers

## Requirements

- Python 3.8+
- See `backend/requirements.txt` for pinned packages (Flask, Flask-CORS, gunicorn)

## Quick start

1. Install dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

2. Audio (committed with the repo):

- The `joke*.mp3` files are committed under `backend/Joke audio/`, so a fresh clone already has them — there is no separate download step. They are named `joke0.mp3`, `joke1.mp3`, … so each index matches the corresponding joke in `Database/clean_base.txt`.
- To add or replace audio, drop files into `backend/Joke audio/` using the same `jokeN.mp3` naming so the index lines up with `clean_base.txt`. Seeding only associates audio that is actually present on disk; a joke with no matching mp3 is still served, just with a `null` `audio_file_path`.

3. Seed the database:

- The database (`backend/jokegen.db`) is not committed — each environment builds its own from `Database/clean_base.txt` and the audio in `backend/Joke audio/`.
- **The app self-seeds on startup:** if `backend/jokegen.db` is missing or has no jokes, the API builds it from `Database/clean_base.txt` the first time it starts. Jokes are inserted whether or not their audio is present (jokes without a matching mp3 get a `null` `audio_file_path`), so the API works on a fresh deploy with no manual step.
- To seed (or re-seed) explicitly — which also associates audio and skips jokes without a matching mp3 — run:

```bash
python Database/db.py
```

Both paths are idempotent and safe to re-run. After running, the SQLite database file will be at `backend/jokegen.db`.

4. Run the API (development):

```bash
cd backend
python app.py
```

Or run with `gunicorn` for a production-like server (from `backend/`):

```bash
gunicorn app:app -w 4 -b 0.0.0.0:5000
```

## Configuration

- `ALLOWED_ORIGINS` — comma-separated list of origins allowed by CORS. Defaults to the production frontend origins (`https://www.nachoaveragedadjoke.com` and the apex `https://nachoaveragedadjoke.com`). Set it to include additional frontend/dev origins, e.g.:

```bash
ALLOWED_ORIGINS="https://www.nachoaveragedadjoke.com,http://localhost:5173" python app.py
```

- `PORT` — port the app listens on (default `5000`).

## Deployment

- Set the start command to run the app with gunicorn from `backend/`, e.g. `gunicorn app:app` (add `-w <n>` for multiple workers).
- No separate seed step is required: the app builds `jokegen.db` from the committed `Database/clean_base.txt` on the **first request** (importing `app.py` has no side effects). Each gunicorn worker seeds once on its first request; seeding is idempotent (`INSERT OR IGNORE` keyed on `joke_number`) so concurrent workers are safe.
- **Audio is served in a default deploy.** The `joke*.mp3` files are committed under `backend/Joke audio/`, so they ship with the app and `/audio/<filename>` works out of the box — the self-seed step sets each joke's audio path from the mp3s present on disk, with no manual step. (Committing the audio keeps deploys zero-config; the tradeoff is a larger repo. For a much larger audio corpus, moving the files to object storage or Git LFS and storing keys in the DB would be the better home.)
- Set `ALLOWED_ORIGINS` to your frontend origin(s) if they differ from the defaults.

### Avoiding free-tier cold starts

On a free tier that spins the service down after a period of inactivity (e.g.
Render's free web service sleeps after 15 minutes and then takes ~30-60s to spin
back up), keep the instance warm by pinging it on a shorter interval. Point a free
uptime monitor (e.g. cron-job.org) at `GET /healthz` **every ~10 minutes**. The
`/healthz` endpoint is dependency-free so pings don't fail while the app is up
(which avoids monitors auto-disabling a job after repeated failures). Enable the
monitor's failure/auto-disable email alerts, and consider a second independent
monitor for redundancy so a single disabled job doesn't bring cold starts back.
Note this stays within Render's free 750 instance-hours/month only if it is the
sole free web service in the workspace.

## Why SQLite, and data persistence

SQLite was chosen because the dataset is small and read-heavy (a fixed corpus of
jokes served to a static frontend) with no concurrent-writer or multi-service
requirements. It needs no separate database server to provision or operate — the
data is a single file built from the committed `Database/clean_base.txt`, which
keeps local dev and deploys zero-config.

The tradeoff is persistence on ephemeral hosts. On platforms like Render's free
tier the container filesystem is not durable: on a cold start or redeploy the
instance starts fresh, `backend/jokegen.db` is gone, and the app simply rebuilds
it from `clean_base.txt` on the first request. Because the joke corpus is the
source of truth in version control, this is fine — nothing is lost. It does mean
**any data written to the SQLite DB at runtime would not survive a restart**, so
the DB is treated as a rebuildable cache, not a system of record. (User favorites
live client-side in `localStorage`, so they are unaffected.) A host with a
persistent disk, or a managed database, would be the path to durable server-side
writes.

## API Endpoints

Each joke is returned as `{ "id", "joke_text", "audio_file_path" }`, where `id` is the stable `joke_number` and `audio_file_path` is a `/audio/...` URL (or `null` if the joke has no audio).

- `GET /random` — return a random joke
- `GET /search?term=...&limit=20&offset=0` — search jokes by text, paginated
  - `term` (required) — text to search for; LIKE wildcards (`%`, `_`) are treated literally
  - `limit` (optional, default `20`, max `100`) — max number of results to return
  - `offset` (optional, default `0`) — number of matching results to skip
  - returns `{ "jokes": [ ... ] }`
- `GET /joke/<number>` — get joke by its `joke_number`; returns `404` if not found
- `GET /audio/<filename>` — serve an audio file from `backend/Joke audio` (sent with a one-week `Cache-Control`)
- `GET /healthz` — lightweight liveness check; returns `{ "status": "ok" }` with `200`. Does no DB/disk/external work, so it can't fail while the app is up. Intended as the target for an uptime pinger (see Deployment).

Examples:

```bash
curl http://localhost:5000/random
curl "http://localhost:5000/search?term=chicken&limit=10&offset=20"
curl http://localhost:5000/joke/12
```

## Testing

```bash
python -m pip install -r backend/requirements-dev.txt
cd backend
python -m pytest tests/
```

## Notes & Troubleshooting

- The Flask app expects `Database/db.py` to expose `get_random_joke`, `search_jokes`, and `get_joke_by_number`. It adds `Database/` to `sys.path` at startup because it is a sibling directory rather than an installed package.
- If the app raises import errors, run `app.py` from the `backend/` directory.
- Audio files are served directly from `backend/Joke audio`. Ensure filenames match those stored in the database (`jokeN.mp3`).
