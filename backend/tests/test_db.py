import sqlite3

import app  # noqa: F401  (importing app adds the Database/ dir to sys.path)
import db


def test_seed_if_empty_populates_and_is_idempotent(tmp_path, monkeypatch):
    # Simulate a deploy with no audio corpus: seeding must still insert jokes,
    # just with a NULL audio path.
    monkeypatch.setattr(db, 'scan_audio_map', lambda _dir: {})

    conn = sqlite3.connect(str(tmp_path / 'seed.db'))
    conn.row_factory = sqlite3.Row
    try:
        assert db.seed_if_empty(conn) is True
        count = db.count_jokes(conn)
        assert count > 0

        # Audio was absent, so no seeded joke should have an audio path.
        with_audio = conn.execute(
            'SELECT COUNT(*) FROM jokes WHERE audio_file_path IS NOT NULL'
        ).fetchone()[0]
        assert with_audio == 0

        # Rows are queryable through the normal search path.
        assert db.search_jokes(conn, 'skeleton')

        # Calling again is a no-op and does not duplicate rows.
        assert db.seed_if_empty(conn) is False
        assert db.count_jokes(conn) == count
    finally:
        conn.close()


def test_seed_if_empty_attaches_available_audio(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'scan_audio_map', lambda _dir: {0: 'joke0.mp3'})

    conn = sqlite3.connect(str(tmp_path / 'seed.db'))
    conn.row_factory = sqlite3.Row
    try:
        db.seed_if_empty(conn)
        row = conn.execute(
            'SELECT audio_file_path FROM jokes WHERE joke_number = 0'
        ).fetchone()
        assert row['audio_file_path'] == 'joke0.mp3'
    finally:
        conn.close()


def test_count_jokes_without_table_returns_zero(tmp_path):
    conn = sqlite3.connect(str(tmp_path / 'empty.db'))
    try:
        assert db.count_jokes(conn) == 0
    finally:
        conn.close()
