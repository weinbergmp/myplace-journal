from datetime import datetime
from flask_login import UserMixin
from .extensions import db
import bcrypt


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode('utf-8'), self.password_hash.encode('utf-8')
        )


class Entry(db.Model):
    __tablename__ = 'entries'

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255))
    body = db.Column(db.Text, nullable=False, default='')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    security = db.Column(db.String(10), nullable=False, default='public')
    mood = db.Column(db.String(100))
    current_music = db.Column(db.String(255))
    tags = db.Column(db.String(500))

    @property
    def is_private(self) -> bool:
        return self.security == 'private'

    @property
    def tag_list(self) -> list[str]:
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]


class SiteSettings(db.Model):
    """Single-row table that stores site-wide customisation options."""
    __tablename__ = 'site_settings'

    id = db.Column(db.Integer, primary_key=True)
    custom_css = db.Column(db.Text, nullable=False, default='')
    theme = db.Column(db.String(50), nullable=False, default='dystopia')

    @classmethod
    def get(cls) -> 'SiteSettings':
        """Return the settings row, creating it if it doesn't exist."""
        row = cls.query.first()
        if row is None:
            row = cls(custom_css='', theme='dystopia')
            db.session.add(row)
            db.session.commit()
        return row
