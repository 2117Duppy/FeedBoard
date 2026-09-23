from flask import Flask, render_template, request, redirect, jsonify, session
import pymysql
import os
import time
import random

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "devops-secret-2026")
app.jinja_env.globals['enumerate'] = enumerate

# In-memory active session tracker
active_sessions = {}
SESSION_TIMEOUT = 300  # 5 minutes

FRIENDS = ["Lucky", "Piddi", "Yashiii", "Dumbooo"]

JOKES = {
    "Lucky": [
        "Lucky is so lucky he once submitted a pull request and it merged itself.",
        "Lucky thought Docker was a brand of shoes. Now he deploys to prod barefoot.",
        "Lucky's WiFi password is 'password123'. His EC2 security group allows 0.0.0.0/0. Living dangerously.",
    ],
    "Piddi": [
        "Piddi once deleted the production database and called it 'cleaning up disk space'.",
        "Piddi's idea of CI/CD is Copy It, Copy it again, Deploy it somehow.",
        "Piddi asked why his container keeps dying. Turns out he named it after himself.",
    ],
    "Yashiii": [
        "Yashiii spent 3 hours debugging a bug. It was a missing semicolon. In Python.",
        "Yashiii's git history is just: 'fix', 'fix fix', 'final fix', 'FINAL fix for real', 'ok this is the last one'.",
        "Yashiii pushed to main directly. The Jenkins pipeline cried.",
    ],
    "Dumbooo": [
        "Dumbooo asked why his Flask app won't start. It was still running from yesterday.",
        "Dumbooo's Dockerfile has 47 RUN commands. Each one installs curl.",
        "Dumbooo SSHed into prod to 'just quickly check something'. We don't talk about what happened next.",
    ],
}

def get_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

def get_messages():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, name FROM Users ORDER BY id")
    messages = cursor.fetchall()
    cursor.close()
    connection.close()
    return messages

def clean_sessions():
    now = time.time()
    expired = [sid for sid, ts in active_sessions.items() if now - ts > SESSION_TIMEOUT]
    for sid in expired:
        del active_sessions[sid]

def track_session():
    if "uid" not in session:
        session["uid"] = os.urandom(8).hex()
    active_sessions[session["uid"]] = time.time()
    clean_sessions()
    return len(active_sessions)

def get_random_joke():
    friend = random.choice(FRIENDS)
    joke = random.choice(JOKES[friend])
    return {"friend": friend, "joke": joke}

@app.route("/")
def home():
    live_count = track_session()
    messages = get_messages()
    joke_data = get_random_joke()
    return render_template(
        "index.html",
        messages=messages,
        live_count=live_count,
        joke=joke_data["joke"],
        joke_friend=joke_data["friend"]
    )

@app.route("/api/live-count")
def live_count_api():
    track_session()
    clean_sessions()
    return jsonify({"count": len(active_sessions)})

@app.route("/add", methods=["POST"])
def add_message():
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "empty"}), 400
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO Users (name) VALUES (%s)", (message,))
    connection.commit()
    cursor.close()
    connection.close()
    messages = get_messages()
    return jsonify([{"id": m[0], "text": m[1]} for m in messages])

@app.route("/delete/<int:user_id>", methods=["POST"])
def delete_message(user_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM Users WHERE id = %s", (user_id,))
    connection.commit()
    cursor.close()
    connection.close()
    messages = get_messages()
    return jsonify([{"id": m[0], "text": m[1]} for m in messages])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)