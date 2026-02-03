# Matcha

A dating website built with Flask and PostgreSQL. Users register, verify email, complete their profile, browse suggestions, like profiles, chat in real time, and receive notifications.

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | Flask (Python) |
| Database | PostgreSQL |
| Frontend | HTML, CSS, JavaScript |
| Real-time | Flask-SocketIO (chat, notifications) |
| Email | Flask-Mail |
| Auth | Flask-Login, Flask-Bcrypt |
| File upload | Werkzeug (images) |
| Location | JavaScript Geolocation API + fallback |

## Prerequisites

- Python 3.8+
- PostgreSQL
- (Optional) SMTP server for email (e.g. Gmail) for verification and password reset

## Installation

1. Clone the repo and go to the project directory:

```bash
cd matcha
```

2. Create a virtual environment and activate it:

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# or: venv\Scripts\activate   # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy environment template and set your values:

```bash
cp .env.example .env
```

Edit `.env`: set `SECRET_KEY`, `DATABASE_URL`, and optionally `MAIL_*` for email.

5. Create the PostgreSQL database:

```bash
createdb matcha_db
```

Or in `psql`: `CREATE DATABASE matcha_db;`

6. Run migrations:

```bash
export FLASK_APP=run.py
flask db init
flask db migrate -m "initial"
flask db upgrade
```

7. (Optional) Create `app/uploads` for user images:

```bash
mkdir -p app/uploads
```

## Environment variables

| Variable | Description | Example |
|----------|-------------|---------|
| `FLASK_APP` | Entry point | `run.py` |
| `FLASK_ENV` | Environment | `development` or `production` |
| `SECRET_KEY` | Session/CSRF secret | Strong random string |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:password@localhost/matcha_db` |
| `MAIL_SERVER` | SMTP host | `smtp.gmail.com` |
| `MAIL_PORT` | SMTP port | `587` |
| `MAIL_USE_TLS` | Use TLS | `True` |
| `MAIL_USERNAME` | SMTP login | Your email |
| `MAIL_PASSWORD` | SMTP password / app password | Your password |
| `UPLOAD_FOLDER` | Path for uploads | `./app/uploads` |
| `MAX_CONTENT_LENGTH` | Max upload size (bytes) | `5242880` (5MB) |


## Run the app

```bash
export FLASK_APP=run.py
flask run
```

Or:

```bash
python run.py
```

By default the app listens on `http://127.0.0.1:5000`. With `run.py` it binds to `0.0.0.0` and port 5000 (or `PORT` env var).

## Project structure

```
matcha/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── models.py            # SQLAlchemy models
│   ├── routes/
│   │   ├── auth.py          # Register, login, logout, verify, reset password
│   │   ├── profile.py       # Profile (stub)
│   │   ├── browse.py        # Suggestions, search (stub)
│   │   ├── chat.py          # Chat (stub)
│   │   └── notifications.py # Notifications (stub)
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/            # register, login, reset_password
│   │   └── browse/          # suggestions, search
│   ├── static/css/style.css
│   ├── utils/
│   │   ├── security.py      # Password validation, sanitization
│   │   ├── email.py         # Verification and reset emails
│   │   └── common_words.txt # For password strength check
│   └── uploads/             # User-uploaded images
├── migrations/               # Flask-Migrate (created by flask db init)
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
├── PROJECT_PLAN.md           # Full roadmap and DB schema
└── README.md
```

## Database schema

- **users** – auth, profile fields, location, fame_rating, email_verified, tokens, is_online, last_seen
- **user_images** – per-user images, profile picture, order
- **tags** / **user_tags** – interest tags (many-to-many)
- **likes** – liker_id, liked_id (unique pair)
- **profile_views** – viewer, viewed, viewed_at
- **blocks** – blocker, blocked (unique pair)
- **reports** – reporter, reported, reason
- **messages** – sender, receiver, content, is_read
- **notifications** – user, type (like, view, message, match, unlike), related_user, is_read
