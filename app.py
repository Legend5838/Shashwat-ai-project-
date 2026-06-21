from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "change_this_secret_key_for_project"
DB_NAME = "database.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            tone TEXT NOT NULL,
            reply TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

def generate_smart_reply(message, tone):
    msg = message.lower().strip()

    if "job" in msg or "interview" in msg:
        base = "Thank you for reaching out. I am interested in this opportunity and would like to know more details about the role, responsibilities, and next steps."
    elif "sorry" in msg or "mistake" in msg:
        base = "I understand the concern. I sincerely apologize for the inconvenience and will make sure this is handled properly."
    elif "meeting" in msg or "schedule" in msg:
        base = "Thank you for the update. Please share a suitable time, and I will confirm my availability for the meeting."
    elif "payment" in msg or "fee" in msg or "money" in msg:
        base = "Thank you for informing me. Please share the complete payment details so I can review and respond accordingly."
    elif "help" in msg or "support" in msg:
        base = "I understand your request. I will check the details and try to help you with the best possible solution."
    else:
        base = "Thank you for your message. I have noted the details and will respond after reviewing the information."

    if tone == "formal":
        return "Dear Sir/Madam,\n\n" + base + "\n\nRegards"
    if tone == "friendly":
        return "Hi,\n\n" + base.replace("Thank you", "Thanks").replace("I am", "I'm") + "\n\nBest wishes"
    if tone == "short":
        return base.split(".")[0] + "."
    return base

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, hashed))
            conn.commit()
            conn.close()
            flash("Registration successful. Please login.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already exists.")
            return redirect(url_for("register"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    generated_reply = None
    user_message = ""
    selected_tone = "formal"

    if request.method == "POST":
        user_message = request.form["message"].strip()
        selected_tone = request.form["tone"]
        generated_reply = generate_smart_reply(user_message, selected_tone)

        conn = get_db()
        conn.execute(
            "INSERT INTO replies (user_id, message, tone, reply, created_at) VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], user_message, selected_tone, generated_reply, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()

    conn = get_db()
    history = conn.execute(
        "SELECT * FROM replies WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("dashboard.html", reply=generated_reply, message=user_message, tone=selected_tone, history=history)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
