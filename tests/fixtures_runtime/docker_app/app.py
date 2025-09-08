"""
Simple Flask application for Docker testing.
"""

from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Hello from Docker Flask!", "status": "ok"})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "health": "healthy"})

@app.route('/api/message')
def api_message():
    return jsonify({"message": "Hello from Docker Flask API!", "data": "test"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
