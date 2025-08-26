# Flask Survey

Простой Flask-проект с регистрацией, входом и 10-вопросным опросником.

Инструкция:
1. Клонируйте репозиторий.
2. Установите зависимости: `pip install -r requirements.txt`
3. Запустите: `python app.py` (или через gunicorn: `gunicorn app:app`)
4. На Render укажите `gunicorn app:app` как команду старта.

Переменные окружения (рекомендовано установить в Render):
- SECRET_KEY — секрет Flask
- ADMIN_PASSWORD — пароль для /admin
