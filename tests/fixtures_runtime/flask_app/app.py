"""
Simple Flask application for testing.
"""

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Hello from Flask!", "status": "ok"})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "health": "healthy"})

@app.route('/api/message')
def api_message():
    return jsonify({"message": "Hello from Flask API!", "data": "test"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
