import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'journal.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    ENTRIES_PER_PAGE = 10
    JOURNAL_TITLE = os.environ.get("JOURNAL_TITLE", "myplace")
    JOURNAL_OWNER = os.environ.get("JOURNAL_OWNER", "journal")
    JOURNAL_SUBTITLE = os.environ.get("JOURNAL_SUBTITLE", "")

    # Google OAuth (optional — omit to disable the Sign in with Google button)
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    # Set to the email address authorised to log in via OAuth
    OAUTH_ALLOWED_EMAIL = os.environ.get("OAUTH_ALLOWED_EMAIL", "")
