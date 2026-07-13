import sqlite3

import pytest

import app as app_module

@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / 'test_jokegen.db'
    conn = sqlite3.connect(str(db_path))
    conn.execute('''
        CREATE TABLE jokes (
            id INTEGER PRIMARY KEY,
            joke_number INTEGER,
            joke_text TEXT,
            audio_file_path TEXT
        )
    ''')
    rows = [
        (1, "Why did the chicken cross the road?", "joke1.mp3"),
        (2, "Knock knock.", None),
        # Wildcard-escaping fixtures: only #3 literally contains "50%".
        (3, "Everything is 50% off today", None),
        (4, "I ate 50 tacos at the fair", None),
        # Pagination fixtures: three jokes sharing the word "pun".
        (5, "pun number one", None),
        (6, "pun number two", None),
        (7, "pun number three", None),
    ]
    conn.executemany(
        "INSERT INTO jokes (joke_number, joke_text, audio_file_path) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(app_module, 'DATABASE_PATH', str(db_path))
    app_module.app.testing = True
    with app_module.app.test_client() as test_client:
        yield test_client

def test_random_joke_returns_joke(client):
    response = client.get('/random')
    assert response.status_code == 200
    data = response.get_json()
    assert 'id' in data
    assert 'joke_text' in data
    assert 'audio_file_path' in data

def test_joke_response_includes_stable_id(client):
    response = client.get('/joke/1')
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == 1

def test_search_returns_matching_jokes(client):
    response = client.get('/search?term=chicken')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['jokes']) == 1
    assert 'chicken' in data['jokes'][0]['joke_text'].lower()

def test_search_without_term_returns_400(client):
    response = client.get('/search')
    assert response.status_code == 400

def test_search_escapes_like_wildcards(client):
    # "50%" must match literally, not as a LIKE pattern (which would also
    # match "50 tacos"). Only the joke containing the literal "50%" qualifies.
    response = client.get('/search?term=50%25')  # %25 is URL-encoded '%'
    assert response.status_code == 200
    jokes = response.get_json()['jokes']
    assert len(jokes) == 1
    assert '50%' in jokes[0]['joke_text']

def test_search_pagination_limit_and_offset(client):
    first = client.get('/search?term=pun&limit=2').get_json()['jokes']
    assert len(first) == 2
    second = client.get('/search?term=pun&limit=2&offset=2').get_json()['jokes']
    assert len(second) == 1
    ids = {j['id'] for j in first} | {j['id'] for j in second}
    assert ids == {5, 6, 7}

def test_joke_by_number_not_found_returns_404(client):
    response = client.get('/joke/999')
    assert response.status_code == 404

def test_joke_by_number_found(client):
    response = client.get('/joke/1')
    assert response.status_code == 200
    data = response.get_json()
    assert data['audio_file_path'] == '/audio/joke1.mp3'

def test_cors_header_for_allowed_origin(client):
    origin = app_module.ALLOWED_ORIGINS[0]
    response = client.get('/random', headers={'Origin': origin})
    assert response.headers.get('Access-Control-Allow-Origin') == origin

def test_cors_header_absent_for_disallowed_origin(client):
    response = client.get('/random', headers={'Origin': 'https://evil.example.com'})
    assert response.headers.get('Access-Control-Allow-Origin') != 'https://evil.example.com'
