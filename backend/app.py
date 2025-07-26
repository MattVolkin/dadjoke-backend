#!/usr/bin/env python3
"""
JokeGen Backend API Skeleton
Connect your database to the frontend
"""


from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os

app = Flask(__name__)
CORS(app)

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Database'))
from database_skeleton import get_random_joke, search_jokes, get_joke_by_number
import sqlite3


DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'jokegen.db')

def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    return connection

@app.route('/random', methods=['GET'])
def get_random_joke_endpoint():
    try:
        conn = get_db_connection()
        joke = get_random_joke(conn)
        conn.close()
        if isinstance(joke[2], list) or isinstance(joke[2], tuple):
            joke_text = '\n'.join(joke[2])
        else:
            joke_text = joke[2]
        audio_filename = os.path.basename(joke[3]) if joke[3] else None
        audio_file_path = f"/audio/{audio_filename}" if audio_filename else None
        return jsonify({'joke_text': joke_text, 'audio_file_path': audio_file_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['GET'])
def search_jokes_endpoint():
    try:
        term = request.args.get('term', '')
        if not term:
            return jsonify({'error': 'Search term required'}), 400
        conn = get_db_connection()
        jokes = search_jokes(conn, term)
        conn.close()
        return jsonify({'jokes': [
            {
                'joke_text': joke[2],
                'audio_file_path': f"/audio/{os.path.basename(joke[3])}" if joke[3] else None
            } for joke in jokes
        ]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/joke/<int:joke_number>', methods=['GET'])
def get_joke_by_number_endpoint(joke_number):
    try:
        conn = get_db_connection()
        joke = get_joke_by_number(conn, joke_number)
        conn.close()
        audio_filename = os.path.basename(joke[3]) if joke[3] else None
        audio_file_path = f"/audio/{audio_filename}" if audio_filename else None
        return jsonify({'joke_text': joke[2], 'audio_file_path': audio_file_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Serve audio files from the 'Joke audio' directory
from flask import send_from_directory

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    audio_dir = os.path.join(os.path.dirname(__file__), 'Joke audio')
    return send_from_directory(audio_dir, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Install dependencies
# RUN pip install flask flask-cors