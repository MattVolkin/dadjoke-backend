#!/usr/bin/env python3
"""
JokeGen Database
Utilities to create, populate, and query the jokes SQLite database.
"""

from pathlib import Path
import random
import re
import sqlite3

def connect_to_database():
    # Place the database file in the backend folder
    backend_dir = Path(__file__).parent.parent / 'backend'
    backend_dir.mkdir(exist_ok=True)
    db_path = backend_dir / 'jokegen.db'
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection

def create_jokes_table(connection):
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jokes (
        id INTEGER PRIMARY KEY,
        joke_number INTEGER,
        joke_text TEXT,
        audio_file_path TEXT
    )
''')
    # We intentionally do NOT index joke_text. Search runs
    # `joke_text LIKE '%term%'`, and a leading-wildcard LIKE cannot use a B-tree
    # index, so such an index would only add write/storage cost without speeding
    # up search. Accelerating substring search would require full-text search
    # (SQLite FTS5), which is out of scope here and would also change matching
    # semantics to token-based rather than literal substring (breaking, e.g.,
    # the literal "50%" behavior). Drop any index left over from older code.
    cursor.execute('DROP INDEX IF EXISTS idx_jokes_joke_text')
    # joke_number is the stable public id and must be unique. The unique index
    # also lets startup seeding use INSERT OR IGNORE so concurrent workers
    # converge on the same rows instead of duplicating them.
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_jokes_joke_number ON jokes(joke_number)')
    connection.commit()


def scan_audio_map(audio_dir):
    """Map joke index -> audio filename for jokeN.mp3 files present on disk.

    Returns an empty map when the directory is absent (e.g. a deploy without
    the gitignored audio corpus), so callers can seed jokes without audio.
    """
    audio_map = {}
    audio_pattern = re.compile(r'joke(\d+)\.mp3')
    for audio_file in Path(audio_dir).glob('joke*.mp3'):
        match = audio_pattern.match(audio_file.name)
        if match:
            audio_map[int(match.group(1))] = audio_file.name
    return audio_map

def read_jokes_from_file(file_path=None):
    """
    Read jokes from a cleaned text file.
    Each joke is separated by a blank line.
    Returns a list of jokes, where each joke is a list of lines.
    """
    # Use default path if none is provided
    if file_path is None:
        script_dir = Path(__file__).parent
        file_path = script_dir / 'clean_base.txt'
    else:
        file_path = Path(file_path)

    # Check if file exists
    if not file_path.exists():
        print(f"Error: Joke file not found at: '{file_path}'")
        return []
    with file_path.open('r', encoding='utf-8') as file:
        file_content = file.read()
        lines = file_content.split('\n\n')
    return lines

def insert_joke(connection, joke_number, joke_text, audio_file_path):
    cursor = connection.cursor()
    cursor.execute('''
        INSERT INTO jokes (joke_number, joke_text, audio_file_path)
        VALUES (?, ?, ?)
    ''', (joke_number, joke_text, audio_file_path))

def populate_database(connection):
    """Populate the database with jokes that have matching audio files based on ID."""
    script_dir = Path(__file__).parent
    jokes_path = script_dir / 'clean_base.txt'
    # Audio lives under backend/, which is also where app.py serves it from.
    audio_dir = script_dir.parent / 'backend' / 'Joke audio'

    print("Reading jokes from file...")
    jokes = read_jokes_from_file(jokes_path)
    print(f"Found {len(jokes)} jokes")

    print("Scanning audio files...")
    audio_map = scan_audio_map(audio_dir)
    print(f"Found {len(audio_map)} audio files")

    print("Creating table...")
    create_jokes_table(connection)

    # Idempotent reseed: clear any existing rows so re-running is safe.
    print("Clearing existing rows...")
    connection.execute('DELETE FROM jokes')

    print("Inserting jokes with audio...")
    inserted_count = 0
    for joke_id, joke in enumerate(jokes):
        if joke_id in audio_map:
            insert_joke(connection, joke_id, joke, audio_map[joke_id])
            inserted_count += 1
        else:
            print(f"Skipping joke #{joke_id}: No matching audio")

    connection.commit()
    print(f"Database populated with {inserted_count} jokes that have audio")

def count_jokes(connection):
    """Return the number of rows in the jokes table, or 0 if it doesn't exist."""
    try:
        return connection.execute('SELECT COUNT(*) FROM jokes').fetchone()[0]
    except sqlite3.OperationalError:
        # Table hasn't been created yet.
        return 0


def seed_if_empty(connection):
    """Create and populate the jokes table if it is missing or empty.

    This lets a fresh environment (such as a deploy with no committed
    jokegen.db) become usable without a manual seed step. Unlike
    populate_database, jokes are inserted whether or not their audio is
    present, so the API works even when the gitignored audio corpus has not
    been deployed (audio_file_path is left NULL for those jokes).

    Safe to call from multiple workers: inserts use INSERT OR IGNORE keyed on
    the unique joke_number, so concurrent seeders converge on the same rows
    rather than duplicating them.

    Returns True if it seeded the table, or False if jokes already existed.
    """
    create_jokes_table(connection)
    if count_jokes(connection) > 0:
        return False

    script_dir = Path(__file__).parent
    jokes = read_jokes_from_file(script_dir / 'clean_base.txt')
    audio_map = scan_audio_map(script_dir.parent / 'backend' / 'Joke audio')

    cursor = connection.cursor()
    for joke_number, joke_text in enumerate(jokes):
        if not joke_text.strip():
            continue
        cursor.execute(
            'INSERT OR IGNORE INTO jokes (joke_number, joke_text, audio_file_path) '
            'VALUES (?, ?, ?)',
            (joke_number, joke_text, audio_map.get(joke_number)),
        )
    connection.commit()
    return True


def get_random_joke(connection):
    # Pick a random row by offset rather than ORDER BY RANDOM(), which sorts
    # the whole table on every call. COUNT + OFFSET stays cheap as the table grows.
    cursor = connection.cursor()
    count = cursor.execute('SELECT COUNT(*) FROM jokes').fetchone()[0]
    if not count:
        return None
    offset = random.randrange(count)
    cursor.execute('SELECT * FROM jokes LIMIT 1 OFFSET ?', (offset,))
    return cursor.fetchone()

def search_jokes(connection, search_term, limit=20, offset=0):
    # Escape LIKE wildcards (% and _) and the escape char itself so a search
    # for "50%" or "a_b" is matched literally rather than as a pattern.
    escaped = (
        search_term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    )
    cursor = connection.cursor()
    cursor.execute(
        r"SELECT * FROM jokes WHERE joke_text LIKE ? ESCAPE '\' LIMIT ? OFFSET ?",
        (f'%{escaped}%', limit, offset),
    )
    jokes = cursor.fetchall()
    return jokes

def get_joke_by_number(connection, joke_number):
    cursor = connection.cursor()
    cursor.execute('''SELECT * FROM jokes WHERE joke_number = ?''', (joke_number,))
    joke = cursor.fetchone()
    return joke

def main():
    """Populate the database from clean_base.txt and run a couple of sanity checks."""
    try:
        connection = connect_to_database()
        populate_database(connection)

        random_joke = get_random_joke(connection)
        print(f"Random joke: {random_joke}")

        search_results = search_jokes(connection, "skeleton")
        print(f"Found {len(search_results)} skeleton jokes")

        if connection:
            connection.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
