# JokeGen Backend

A small Flask backend for serving jokes, search, and optional audio files to a static frontend.

## Repository Structure

- `backend/` — Flask API and application files
  - `app.py` — main Flask application exposing the API
  - `requirements.txt` — Python dependencies
  - `requirements-dev.txt` — dependencies for running tests (includes `requirements.txt`)
  - `tests/` — pytest test suite
  - `Joke audio/` — directory (optional) containing `joke*.mp3` audio files served by the app
- `Database/` — helper scripts for creating and populating the SQLite database
  - `db.py` — utilities to create `jokegen.db`, read `clean_base.txt`, and populate the DB
  - `clean_base.txt` — cleaned jokes source (plain text)
  - `clean_base.py` — one-off script that produces `clean_base.txt` from a raw `base.txt`

## Features

- Serve random jokes and search by text, with pagination
- Retrieve specific jokes by number
- Optionally serve pre-recorded joke audio files from `backend/Joke audio`

## Requirements

- Python 3.8+
- See `backend/requirements.txt` for pinned packages (Flask, Flask-CORS, gunicorn)

## Quick start

1. Install dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

2. Seed the database:

- The database (`backend/jokegen.db`) is not committed to the repo (see `.gitignore`) — each environment builds its own from `Database/clean_base.txt` and the audio files in `Joke audio/`.
- `Database/db.py` contains the helpers to create and populate `jokegen.db` in the `backend/` folder. Edit or supply `Database/clean_base.txt` and put audio files named like `joke0.mp3`, `joke1.mp3`, … in the `Joke audio/` folder.

Run the population script from the repository root:

```bash
python Database/db.py
```

After running, the SQLite database file will be placed at `backend/jokegen.db`.

3. Run the API (development):

```bash
cd backend
python app.py
```

Or run with `gunicorn` for a production-like server (from `backend/`):

```bash
gunicorn app:app -w 4 -b 0.0.0.0:5000
```

## API Endpoints

- `GET /random` — return a random joke (JSON: `joke_text`, `audio_file_path`)
- `GET /search?term=...&limit=20&offset=0` — search jokes by text, paginated
  - `term` (required) — text to search for
  - `limit` (optional, default `20`, max `100`) — max number of results to return
  - `offset` (optional, default `0`) — number of matching results to skip
- `GET /joke/<number>` — get joke by its `joke_number`; returns `404` if not found
- `GET /audio/<filename>` — serve an audio file from the `Joke audio` folder

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

- The Flask app expects `Database/db.py` to expose `get_random_joke`, `search_jokes`, and `get_joke_by_number`.
- If the app raises import errors, ensure the working directory and `sys.path` are configured so `Database` is importable; running `app.py` from the `backend/` directory is recommended.
- Audio files are served directly from the `backend/Joke audio` directory. Ensure filenames match those stored in the database.
- `Joke audio/` is committed directly since the app serves it as-is. If the audio collection grows much larger, consider migrating it to [Git LFS](https://git-lfs.com/) instead of committing the raw files.
