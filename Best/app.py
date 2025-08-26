import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from io import StringIO
import csv
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'survey.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-secret')

QUESTIONS = [
    "Чем вы увлекаетесь?",
    "Что вы любите делать в свободное время?",
    "Какой ваш любимый жанр музыки?",
    "Любите ли вы путешествовать? Куда бы хотели поехать?",
    "Есть ли у вас домашние животные?",
    "Какой ваш любимый фильм/сериал?",
    "Увлекаетесь ли вы спортом? Каким?",
    "Какую еду вы предпочитаете?",
    "Есть ли у вас хобби, о котором мало кто знает?",
    "Чего вы хотите достичь в ближайшие 5 лет?"
]

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            answers TEXT,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

if not os.path.exists(DB_PATH):
    init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form['password']
        if not email or not password:
            flash('Email и пароль обязательны')
            return redirect(url_for('register'))
        pw_hash = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (email, phone, password_hash, created_at) VALUES (?,?,?,?)',
                         (email, phone, pw_hash, datetime.utcnow().isoformat()))
            conn.commit()
            flash('Регистрация прошла успешно. Войдите.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Пользователь с таким email уже существует')
            return redirect(url_for('register'))
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['email'] = user['email']
            flash('Вход выполнен')
            return redirect(url_for('survey'))
        else:
            flash('Неверный email или пароль')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли')
    return redirect(url_for('index'))

@app.route('/survey', methods=['GET', 'POST'])
def survey():
    if 'user_id' not in session:
        flash('Пожалуйста, войдите чтобы пройти опрос')
        return redirect(url_for('login'))
    if request.method == 'POST':
        answers = []
        for i in range(len(QUESTIONS)):
            answers.append(request.form.get(f'q{i}', '').strip())
        answers_str = '||'.join(answers)
        conn = get_db_connection()
        conn.execute('INSERT INTO responses (user_id, answers, created_at) VALUES (?,?,?)',
                     (session['user_id'], answers_str, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        return render_template('thanks.html')
    return render_template('survey.html', questions=QUESTIONS)

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        p = request.form.get('admin_pass', '')
        if p != ADMIN_PASSWORD:
            flash('Неверный пароль администратора')
            return redirect(url_for('admin'))
        session['is_admin'] = True
        return redirect(url_for('admin'))
    if not session.get('is_admin'):
        return render_template('admin.html', entries=None, require_pass=True)

    conn = get_db_connection()
    rows = conn.execute('SELECT r.id, r.user_id, r.answers, r.created_at, u.email, u.phone FROM responses r LEFT JOIN users u ON u.id = r.user_id ORDER BY r.created_at DESC').fetchall()
    conn.close()
    entries = []
    for row in rows:
        answers = row['answers'].split('||') if row['answers'] else []
        entries.append({'id': row['id'], 'user_id': row['user_id'], 'email': row['email'], 'phone': row['phone'], 'answers': answers, 'created_at': row['created_at']})
    return render_template('admin.html', entries=entries, require_pass=False, questions=QUESTIONS)

@app.route('/admin/export')
def admin_export():
    if not session.get('is_admin'):
        flash('Требуется вход администратора')
        return redirect(url_for('admin'))
    conn = get_db_connection()
    rows = conn.execute('SELECT r.id, r.user_id, r.answers, r.created_at, u.email, u.phone FROM responses r LEFT JOIN users u ON u.id = r.user_id ORDER BY r.created_at DESC').fetchall()
    conn.close()
    si = StringIO()
    cw = csv.writer(si)
    header = ['id','user_id','email','phone','created_at'] + [f'q{i+1}' for i in range(len(QUESTIONS))]
    cw.writerow(header)
    for row in rows:
        answers = (row['answers'] or '').split('||')
        cw.writerow([row['id'], row['user_id'], row['email'], row['phone'], row['created_at']] + answers)
    si.seek(0)
    return send_file(
        StringIO(si.getvalue()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='responses.csv'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
