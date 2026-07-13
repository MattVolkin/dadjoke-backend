# JokeGen Backend

A small Flask + SQLite backend for serving jokes, search, and audio to a static frontend.

## Repository Structure

- `backend/` — Flask API and application files
  - `app.py` — main Flask application exposing the API
  - `requirements.txt` — Python dependencies
  - `requirements-dev.txt` — dependencies for running tests (includes `requirements.txt`)
  - `tests/` — pytest test suite
  - `Joke audio/` — local (gitignored) directory of `joke*.mp3` files served by the app
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

2. Obtain the audio (not committed):

- Audio files are **not** tracked in git (they are gitignored, matching the frontend). Place your `joke*.mp3` files in `backend/Joke audio/`, named `joke0.mp3`, `joke1.mp3`, … so each index matches the corresponding joke in `Database/clean_base.txt`.
- The database and seeding step only associate audio that is actually present on disk; jokes without a matching mp3 are skipped.

3. Seed the database:

- The database (`backend/jokegen.db`) is not committed — each environment builds its own from `Database/clean_base.txt` and the audio in `backend/Joke audio/`.
- Seeding is idempotent: running it again recreates the table if needed and replaces existing rows, so it is safe to re-run.

```bash
python Database/db.py
```

After running, the SQLite database file will be at `backend/jokegen.db`.

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

- `ALLOWED_ORIGINS` — comma-separated list of origins allowed by CORS. Defaults to the production frontend origin (`https://www.nachoaveragedadjoke.com`). Set it to include additional frontend/dev origins, e.g.:

```bash
ALLOWED_ORIGINS="https://www.nachoaveragedadjoke.com,http://localhost:5173" python app.py
```

- `PORT` — port the app listens on (default `5000`).

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
