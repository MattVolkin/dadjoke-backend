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
    conn.execute(
        "INSERT INTO jokes (joke_number, joke_text, audio_file_path) VALUES (?, ?, ?)",
        (1, "Why did the chicken cross the road?", "joke1.mp3"),
    )
    conn.execute(
        "INSERT INTO jokes (joke_number, joke_text, audio_file_path) VALUES (?, ?, ?)",
        (2, "Knock knock.", None),
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
    assert 'joke_text' in data
    assert 'audio_file_path' in data

def test_search_returns_matching_jokes(client):
    response = client.get('/search?term=chicken')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['jokes']) == 1
    assert 'chicken' in data['jokes'][0]['joke_text'].lower()

def test_search_without_term_returns_400(client):
    response = client.get('/search')
    assert response.status_code == 400

def test_joke_by_number_not_found_returns_404(client):
    response = client.get('/joke/999')
    assert response.status_code == 404

def test_joke_by_number_found(client):
    response = client.get('/joke/1')
    assert response.status_code == 200
    data = response.get_json()
    assert data['audio_file_path'] == '/audio/joke1.mp3'
