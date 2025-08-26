import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            password TEXT NOT NULL
        );
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS answers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            q1 TEXT, q2 TEXT, q3 TEXT, q4 TEXT, q5 TEXT,
            q6 TEXT, q7 TEXT, q8 TEXT, q9 TEXT, q10 TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    db.commit()

# вызываем сразу при старте, чтобы база была готова
with app.app_context():
    init_db()

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("questions"))
    return redirect(url_for("register"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        if not (name and email and phone and password):
            return render_template("register.html", error="Заполни все поля.")
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users(name,email,phone,password) VALUES(?,?,?,?)",
                (name, email, phone, password),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Такой email уже зарегистрирован.")
        user_id = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]
        session["user_id"] = user_id
        session["name"] = name
        return redirect(url_for("questions"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email=? AND password=?", (email, password)
        ).fetchone()
        if user:
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            return redirect(url_for("questions"))
        return render_template("login.html", error="Неверный email или пароль.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

QUESTIONS = [
    "Какие цветы тебе нравятся?",
    "Где ты любишь путешествовать?",
    "Какое твоё любимое блюдо?",
    "Какая музыка тебе нравится?",
    "Какой у тебя любимый фильм?",
    "Какая у тебя любимая книга?",
    "Чем ты любишь заниматься в свободное время?",
    "Какая у тебя любимая время года?",
    "Какой вид спорта тебе нравится?",
    "О чём ты мечтаешь?",
]

@app.route("/questions", methods=["GET", "POST"])
def questions():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    if request.method == "POST":
        answers = [request.form.get(f"q{i}", "").strip() for i in range(1, 11)]
        existing = db.execute(
            "SELECT id FROM answers WHERE user_id=?", (session["user_id"],)
        ).fetchone()
        if existing:
            db.execute(
                """
                UPDATE answers SET
                    q1=?, q2=?, q3=?, q4=?, q5=?, q6=?, q7=?, q8=?, q9=?, q10=?
                WHERE user_id=?
                """,
                (*answers, session["user_id"]),
            )
        else:
            db.execute(
                """
                INSERT INTO answers (user_id, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session["user_id"], *answers),
            )
        db.commit()
        row = db.execute("SELECT * FROM answers WHERE user_id=?", (session["user_id"],)).fetchone()
        prefill = [row[f"q{i}"] if row else "" for i in range(1, 11)]
        return render_template("questions.html", questions=QUESTIONS, saved=True, prefill=prefill)
    row = db.execute("SELECT * FROM answers WHERE user_id=?", (session["user_id"],)).fetchone()
    prefill = [row[f"q{i}"] if row else "" for i in range(1, 11)]
    return render_template("questions.html", questions=QUESTIONS, prefill=prefill)

@app.route("/admin")
def admin():
    db = get_db()
    rows = db.execute(
        """
        SELECT u.name, u.email, u.phone,
               a.q1, a.q2, a.q3, a.q4, a.q5, a.q6, a.q7, a.q8, a.q9, a.q10
        FROM users u
        LEFT JOIN answers a ON a.user_id = u.id
        ORDER BY u.id DESC
        """
    ).fetchall()
    return render_template("admin.html", rows=rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

