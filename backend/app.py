#!/usr/bin/env python3
"""
JokeGen Backend API
Connects the jokes database to the frontend
"""

import logging
import os
import sqlite3
import sys
import threading
from contextlib import contextmanager

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)

# Restrict CORS to an allowlist. ALLOWED_ORIGINS is a comma-separated list of
# origins; it defaults to the production frontend origin. Set it (e.g. to add a
# localhost dev origin) rather than opening the API to all origins.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS",
        "https://www.nachoaveragedadjoke.com,https://nachoaveragedadjoke.com",
    ).split(",")
    if origin.strip()
]
CORS(app, origins=ALLOWED_ORIGINS)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The DB helpers live in the sibling Database/ directory, which is not an
# installed package (this repo has no packaging/setup). Add it to sys.path so
# `import db` works regardless of the current working directory.
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Database'))
try:
    from db import get_random_joke, search_jokes, get_joke_by_number, seed_if_empty
except ImportError as e:
    logger.error(f"Error importing db module: {e}")
    raise

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'jokegen.db')
AUDIO_DIR = os.path.join(os.path.dirname(__file__), 'Joke audio')

DEFAULT_SEARCH_LIMIT = 20
MAX_SEARCH_LIMIT = 100

# Audio files are content-addressed by name and effectively immutable, so let
# clients and CDNs cache them for a week.
AUDIO_MAX_AGE = 60 * 60 * 24 * 7

@contextmanager
def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def _ensure_database_seeded():
    """Seed the database on startup if it is missing or empty.

    Deploys (e.g. Render) start with no committed jokegen.db; without this the
    first query would fail with "no such table: jokes" and every request would
    return a 500. Seeding here builds the table from Database/clean_base.txt so
    the API is usable on a fresh environment with no manual step.
    """
    try:
        with get_db_connection() as conn:
            if seed_if_empty(conn):
                logger.info("Seeded jokes database at %s", DATABASE_PATH)
    except Exception:
        logger.exception("Failed to seed database on startup")


# Seed on the first request rather than at import time, so importing app.py has
# no side effects (relevant for tests, tooling, and `flask` CLI introspection).
# Under gunicorn this runs once per worker on its first request; seed_if_empty is
# idempotent (INSERT OR IGNORE keyed on joke_number) so concurrent workers are safe.
_seed_lock = threading.Lock()
_seeded = False


@app.before_request
def _seed_on_first_request():
    global _seeded
    if _seeded:
        return
    with _seed_lock:
        if not _seeded:
            _ensure_database_seeded()
            _seeded = True

def _joke_response(joke):
    joke_text = joke['joke_text']
    if isinstance(joke_text, (list, tuple)):
        joke_text = '\n'.join(joke_text)
    audio_filename = os.path.basename(joke['audio_file_path']) if joke['audio_file_path'] else None
    audio_file_path = f"/audio/{audio_filename}" if audio_filename else None
    # Expose joke_number as a stable `id` so clients can key on it rather than joke text.
    return {'id': joke['joke_number'], 'joke_text': joke_text, 'audio_file_path': audio_file_path}

@app.route('/random', methods=['GET'])
def get_random_joke_endpoint():
    try:
        with get_db_connection() as conn:
            joke = get_random_joke(conn)

        if joke is None:
            return jsonify({'error': 'No jokes found in database'}), 404

        return jsonify(_joke_response(joke))
    except Exception:
        logger.exception("Error in get_random_joke_endpoint")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/search', methods=['GET'])
def search_jokes_endpoint():
    try:
        term = request.args.get('term', '')
        if not term:
            return jsonify({'error': 'Search term required'}), 400

        try:
            limit = int(request.args.get('limit', DEFAULT_SEARCH_LIMIT))
            offset = int(request.args.get('offset', 0))
        except ValueError:
            return jsonify({'error': 'limit and offset must be integers'}), 400

        limit = max(1, min(limit, MAX_SEARCH_LIMIT))
        offset = max(0, offset)

        with get_db_connection() as conn:
            jokes = search_jokes(conn, term, limit=limit, offset=offset)

        return jsonify({'jokes': [_joke_response(joke) for joke in jokes]})
    except Exception:
        logger.exception("Error in search_jokes_endpoint")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/joke/<int:joke_number>', methods=['GET'])
def get_joke_by_number_endpoint(joke_number):
    try:
        with get_db_connection() as conn:
            joke = get_joke_by_number(conn, joke_number)

        if joke is None:
            return jsonify({'error': 'Joke not found'}), 404

        return jsonify(_joke_response(joke))
    except Exception:
        logger.exception("Error in get_joke_by_number_endpoint")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename, max_age=AUDIO_MAX_AGE)

@app.route('/healthz', methods=['GET'])
def healthz():
    # Lightweight liveness check with no DB/disk/external dependency, used as the
    # target for uptime pingers that keep the free-tier instance from spinning
    # down. Kept dependency-free so a ping can't fail while the app is up.
    return jsonify({'status': 'ok'}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
