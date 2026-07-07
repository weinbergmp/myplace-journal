import os
import click
from flask import Flask
from config import Config
from .extensions import db, migrate, login_manager, csrf, oauth


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Allow OAuth over plain http in development
    if app.debug or app.testing:
        os.environ.setdefault('AUTHLIB_INSECURE_TRANSPORT', '1')

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)

    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    from .models import User  # noqa: F401 — register model with SQLAlchemy

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .utils import render_markdown, lj_date
    app.jinja_env.filters['markdown'] = render_markdown
    app.jinja_env.globals['lj_date'] = lj_date

    # Register Google OAuth provider if credentials are configured
    if app.config.get('GOOGLE_CLIENT_ID'):
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )

    from .routes import bp
    app.register_blueprint(bp)

    @app.cli.command('create-user')
    @click.argument('username')
    @click.password_option()
    def create_user_cmd(username, password):
        """Create the journal owner account."""
        user = User.query.filter_by(username=username).first()
        if user:
            click.echo(f"User '{username}' already exists.")
            return
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"User '{username}' created successfully.")

    @app.cli.command('init-db')
    def init_db_cmd():
        """Create all database tables and apply lightweight column migrations."""
        db.create_all()
        # Idempotent migration: add 'theme' column to site_settings if absent.
        # SQLite supports ADD COLUMN; the except swallows the duplicate-column error.
        from sqlalchemy import text
        with db.engine.connect() as conn:
            try:
                conn.execute(text(
                    "ALTER TABLE site_settings "
                    "ADD COLUMN theme VARCHAR(50) NOT NULL DEFAULT 'dystopia'"
                ))
                conn.commit()
            except Exception:
                pass  # column already exists — nothing to do
        click.echo('Database ready.')

    return app
