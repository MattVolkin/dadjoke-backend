# JokeGen Backend

A small Flask backend for serving jokes and optional audio files. Intended as a learning skeleton to connect a jokes database and audio assets to a frontend.

## Repository Structure

- `backend/` — Flask API and application files
  - `app.py` — main Flask application exposing the API
  - `requirements.txt` — Python dependencies
  - `Joke audio/` — directory (optional) containing `joke*.mp3` audio files served by the app
- `Database/` — helper scripts for creating and populating the SQLite database
  - `database_skeleton.py` — utilities to create `jokegen.db`, read `clean_base.txt`, and populate the DB
  - `clean_base.txt` — cleaned jokes source (plain text)

## Features

- Serve random jokes and search by text
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

2. (Optional) Populate the database:

- The `Database/database_skeleton.py` script contains helpers to create and populate `jokegen.db` in the `backend/` folder. Edit or supply `Database/clean_base.txt` and put audio files named like `joke0.mp3`, `joke1.mp3`, … in the `Joke audio/` folder.

Run the population script from the repository root:

```bash
python Database/database_skeleton.py
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
- `GET /search?term=...` — search jokes by text, returns matching jokes
- `GET /joke/<number>` — get joke by its `joke_number`
- `GET /audio/<filename>` — serve an audio file from the `Joke audio` folder

Examples:

```bash
curl http://localhost:5000/random
curl "http://localhost:5000/search?term=chicken"
curl http://localhost:5000/joke/12
```

## Notes & Troubleshooting

- The Flask app expects `Database/database_skeleton.py` to expose `get_random_joke`, `search_jokes`, and `get_joke_by_number` (already implemented in the skeleton).
- If the app raises import errors, ensure the working directory and `sys.path` are configured so `Database` is importable; running `app.py` from the `backend/` directory is recommended.
- Audio files are served directly from the `backend/Joke audio` directory. Ensure filenames match those stored in the database.

## Contributing

Improvements welcome. Typical tasks:

- Add input validation and better error handling
- Add pagination to the `search` endpoint
- Improve the database schema and migration support

## License

This repository does not include a license. Add one if you plan to publish or reuse code publicly.
