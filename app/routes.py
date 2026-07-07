import calendar
from collections import defaultdict
from datetime import datetime, date

from flask import (Blueprint, render_template, request, redirect, url_for,
                   abort, flash, current_app)
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import extract, func, or_

from .extensions import db
from .models import Entry, User, SiteSettings
from .forms import EntryForm, LoginForm, SettingsForm
from .utils import lj_date
from .extensions import oauth

bp = Blueprint('main', __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _visible_entries(include_private: bool):
    """Base queryset filtered by auth state, newest-first."""
    q = Entry.query.order_by(Entry.created_at.desc())
    if not include_private:
        q = q.filter(Entry.security == 'public')
    return q


# ---------------------------------------------------------------------------
# Context processor — sidebar data injected into every template
# ---------------------------------------------------------------------------

@bp.context_processor
def inject_sidebar():
    today = date.today()
    year, month = today.year, today.month

    month_q = Entry.query.filter(
        extract('year', Entry.created_at) == year,
        extract('month', Entry.created_at) == month,
    )
    if not current_user.is_authenticated:
        month_q = month_q.filter(Entry.security == 'public')

    entry_days = {e.created_at.day for e in month_q.with_entities(Entry.created_at).all()}

    cal = calendar.Calendar(firstweekday=6)  # Sunday first, classic LJ style
    weeks = cal.monthdayscalendar(year, month)

    # Collect all tags (public-only when logged out)
    tag_q = Entry.query
    if not current_user.is_authenticated:
        tag_q = tag_q.filter(Entry.security == 'public')
    all_tags: dict[str, int] = defaultdict(int)
    for (raw_tags,) in tag_q.with_entities(Entry.tags).all():
        for tag in (raw_tags or '').split(','):
            tag = tag.strip()
            if tag:
                all_tags[tag] += 1

    _settings = SiteSettings.get()

    return dict(
        sidebar_year=year,
        sidebar_month=month,
        sidebar_month_name=calendar.month_name[month],
        sidebar_weeks=weeks,
        sidebar_entry_days=entry_days,
        sidebar_tags=dict(sorted(all_tags.items())),
        custom_css=_settings.custom_css or '',
        site_theme=_settings.theme or 'dystopia',
    )


# ---------------------------------------------------------------------------
# Journal index
# ---------------------------------------------------------------------------

@bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ENTRIES_PER_PAGE']
    pagination = _visible_entries(current_user.is_authenticated).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('index.html', pagination=pagination)


# ---------------------------------------------------------------------------
# Single entry
# ---------------------------------------------------------------------------

@bp.route('/entry/<int:entry_id>')
def entry(entry_id):
    e = db.get_or_404(Entry, entry_id)
    if e.is_private and not current_user.is_authenticated:
        abort(404)

    prev_entry = (
        _visible_entries(current_user.is_authenticated)
        .filter(Entry.created_at < e.created_at)
        .first()
    )
    next_entry = (
        _visible_entries(current_user.is_authenticated)
        .filter(Entry.created_at > e.created_at)
        .order_by(Entry.created_at.asc())
        .first()
    )

    return render_template(
        'entry.html', entry=e, prev_entry=prev_entry, next_entry=next_entry
    )


# ---------------------------------------------------------------------------
# Write / Edit / Delete
# ---------------------------------------------------------------------------

@bp.route('/write', methods=['GET', 'POST'])
@login_required
def write():
    form = EntryForm()
    if form.validate_on_submit():
        e = Entry(
            subject=(form.subject.data or '').strip() or None,
            body=form.body.data,
            security=form.security.data,
            mood=(form.mood.data or '').strip() or None,
            current_music=(form.current_music.data or '').strip() or None,
            tags=(form.tags.data or '').strip() or None,
        )
        db.session.add(e)
        db.session.commit()
        flash('Entry posted.', 'success')
        return redirect(url_for('main.entry', entry_id=e.id))
    return render_template('write.html', form=form, edit_mode=False)


@bp.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def edit(entry_id):
    e = db.get_or_404(Entry, entry_id)
    form = EntryForm(obj=e)
    if form.validate_on_submit():
        e.subject = (form.subject.data or '').strip() or None
        e.body = form.body.data
        e.security = form.security.data
        e.mood = (form.mood.data or '').strip() or None
        e.current_music = (form.current_music.data or '').strip() or None
        e.tags = (form.tags.data or '').strip() or None
        e.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Entry updated.', 'success')
        return redirect(url_for('main.entry', entry_id=e.id))
    return render_template('write.html', form=form, edit_mode=True, entry=e)


@bp.route('/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete(entry_id):
    e = db.get_or_404(Entry, entry_id)
    db.session.delete(e)
    db.session.commit()
    flash('Entry deleted.', 'info')
    return redirect(url_for('main.index'))


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

@bp.route('/calendar')
@bp.route('/calendar/<int:year>/<int:month>')
def calendar_view(year=None, month=None):
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    if not (1 <= month <= 12):
        abort(404)

    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(year, month)

    month_entries = Entry.query.filter(
        extract('year', Entry.created_at) == year,
        extract('month', Entry.created_at) == month,
    )
    if not current_user.is_authenticated:
        month_entries = month_entries.filter(Entry.security == 'public')
    month_entries = month_entries.order_by(Entry.created_at.asc()).all()

    entries_by_day: dict[int, list] = defaultdict(list)
    for e in month_entries:
        entries_by_day[e.created_at.day].append(e)

    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year
    next_month = month % 12 + 1
    next_year = year + 1 if month == 12 else year

    return render_template(
        'calendar.html',
        year=year, month=month,
        month_name=calendar.month_name[month],
        weeks=weeks,
        entries_by_day=dict(entries_by_day),
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,
        today=today,
    )


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

@bp.route('/archive')
def archive():
    q = Entry.query
    if not current_user.is_authenticated:
        q = q.filter(Entry.security == 'public')

    rows = (
        q.with_entities(
            extract('year', Entry.created_at).label('yr'),
            extract('month', Entry.created_at).label('mo'),
            func.count(Entry.id).label('cnt'),
        )
        .group_by('yr', 'mo')
        .order_by(extract('year', Entry.created_at).desc(),
                  extract('month', Entry.created_at).desc())
        .all()
    )

    archive_data: dict[int, list] = defaultdict(list)
    for row in rows:
        yr, mo = int(row.yr), int(row.mo)
        archive_data[yr].append((mo, calendar.month_name[mo], row.cnt))

    return render_template(
        'archive.html',
        archive_data=dict(sorted(archive_data.items(), reverse=True)),
    )


# ---------------------------------------------------------------------------
# Tag view
# ---------------------------------------------------------------------------

@bp.route('/tag/<tag>')
def tag_view(tag):
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ENTRIES_PER_PAGE']

    q = _visible_entries(current_user.is_authenticated).filter(
        or_(
            Entry.tags == tag,
            Entry.tags.like(f'{tag},%'),
            Entry.tags.like(f'%,{tag}'),
            Entry.tags.like(f'%,{tag},%'),
            Entry.tags.like(f'%, {tag}'),
            Entry.tags.like(f'%, {tag},%'),
            Entry.tags.like(f'{tag}, %'),
        )
    )

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('tag.html', tag=tag, pagination=pagination)


# ---------------------------------------------------------------------------
# User info (static profile page)
# ---------------------------------------------------------------------------

@bp.route('/userinfo')
def userinfo():
    return render_template('userinfo.html')


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    site = SiteSettings.get()
    form = SettingsForm(obj=site)
    if form.validate_on_submit():
        site.custom_css = (form.custom_css.data or '').strip()
        site.theme = form.theme.data or 'dystopia'
        db.session.commit()
        flash('Settings saved.', 'success')
        return redirect(url_for('main.settings'))
    return render_template('settings.html', form=form)


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

@bp.route('/auth/google')
def google_login():
    if not current_app.config.get('GOOGLE_CLIENT_ID'):
        flash('Google login is not configured on this instance.', 'error')
        return redirect(url_for('main.login'))
    redirect_uri = url_for('main.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@bp.route('/auth/google/callback')
def google_callback():
    if not current_app.config.get('GOOGLE_CLIENT_ID'):
        abort(404)
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash('Google sign-in failed. Please try again.', 'error')
        return redirect(url_for('main.login'))

    userinfo = token.get('userinfo') or {}
    email = (userinfo.get('email') or '').lower()

    allowed = (current_app.config.get('OAUTH_ALLOWED_EMAIL') or '').lower()
    if allowed and email != allowed:
        flash('That Google account is not authorised to access this journal.', 'error')
        return redirect(url_for('main.login'))

    user = User.query.first()
    if not user:
        flash('No journal account exists yet. Run flask create-user first.', 'error')
        return redirect(url_for('main.login'))

    login_user(user, remember=True)
    flash(f'Signed in with Google ({email}).', 'success')
    return redirect(url_for('main.index'))
