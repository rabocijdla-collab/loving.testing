from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT, 
                  password TEXT, 
                  phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS answers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  user_id INTEGER, 
                  question TEXT, 
                  answer TEXT)''')
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        phone = request.form["phone"]
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, phone) VALUES (?, ?, ?)", (username, password, phone))
        conn.commit()
        conn.close()
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session["user_id"] = user[0]
            return redirect("/survey")
    return render_template("login.html")

@app.route("/survey", methods=["GET", "POST"])
def survey():
    questions = [
        "Чем ты увлекаешься?",
        "Что ты любишь есть?",
        "Какие фильмы нравятся?",
        "Любимое место отдыха?",
        "Любимая музыка?",
        "Какой спорт нравится?",
        "Любимое животное?",
        "Что тебя мотивирует?",
        "Любимый цвет?",
        "Мечтаешь о чём?"
    ]
    if "user_id" not in session:
        return redirect("/login")
    if request.method == "POST":
        answers = request.form.to_dict()
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        for q, a in answers.items():
            c.execute("INSERT INTO answers (user_id, question, answer) VALUES (?, ?, ?)", (session["user_id"], q, a))
        conn.commit()
        conn.close()
        return "Спасибо за ответы!"
    return render_template("survey.html", questions=questions)

@app.route("/admin")
def admin():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT users.username, users.phone, answers.question, answers.answer FROM answers JOIN users ON users.id = answers.user_id")
    data = c.fetchall()
    conn.close()
    return render_template("admin.html", data=data)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
