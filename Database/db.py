#!/usr/bin/env python3
"""
JokeGen Database
Utilities to create, populate, and query the jokes SQLite database.
"""

from pathlib import Path
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
    CREATE TABLE jokes (
        id INTEGER PRIMARY KEY,
        joke_number INTEGER,
        joke_text TEXT,
        audio_file_path TEXT
    )
''')
    connection.commit()

def read_jokes_from_file(file_path=None, verbose=False):
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
    jokes_path = script_dir.parent / 'Database' / 'clean_base.txt'
    audio_dir = script_dir.parent / 'Joke audio'

    print("Reading jokes from file...")
    jokes = read_jokes_from_file(jokes_path, verbose=True)
    print(f"Found {len(jokes)} jokes")

    print("Scanning audio files...")
    audio_map = {}

    audio_pattern = re.compile(r'joke(\d+)\.mp3')
    for audio_file in audio_dir.glob('joke*.mp3'):
        match = audio_pattern.match(audio_file.name)
        if match:
            joke_id = int(match.group(1))
            audio_map[joke_id] = audio_file.name

    print(f"Found {len(audio_map)} audio files")

    print("Creating table...")
    create_jokes_table(connection)

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

def get_random_joke(connection):
    cursor = connection.cursor()
    cursor.execute('''SELECT * FROM jokes ORDER BY RANDOM() LIMIT 1''')
    joke = cursor.fetchone()
    return joke

def search_jokes(connection, search_term, limit=20, offset=0):
    cursor = connection.cursor()
    cursor.execute(
        '''SELECT * FROM jokes WHERE joke_text LIKE ? LIMIT ? OFFSET ?''',
        (f'%{search_term}%', limit, offset),
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
