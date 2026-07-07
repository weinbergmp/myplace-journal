from datetime import datetime
import markdown
import bleach
from markupsafe import Markup

_ALLOWED_TAGS = {
    'a', 'abbr', 'b', 'blockquote', 'br', 'code', 'del', 'em',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
    'li', 'ol', 'p', 'pre', 's', 'strong', 'table', 'tbody',
    'td', 'th', 'thead', 'tr', 'ul',
}
_ALLOWED_ATTRS: dict = {
    'a': ['href', 'title', 'rel'],
    'img': ['src', 'alt', 'title'],
    '*': ['class'],
}

_MONTH_ABBR = [
    '', 'Jan.', 'Feb.', 'Mar.', 'Apr.', 'May', 'Jun.',
    'Jul.', 'Aug.', 'Sep.', 'Oct.', 'Nov.', 'Dec.',
]


def render_markdown(text: str) -> Markup:
    """Convert Markdown to sanitised HTML, safe for use with Jinja2's | markdown filter."""
    if not text:
        return Markup('')
    html = markdown.markdown(
        text,
        extensions=['extra', 'nl2br', 'sane_lists'],
    )
    clean = bleach.clean(html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)
    return Markup(clean)


def ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suffix}'


def lj_date(dt: datetime) -> str:
    """Format a datetime in classic LiveJournal style: 'Jul. 6th, 2026 | 10:45 pm'"""
    month = _MONTH_ABBR[dt.month]
    day = ordinal(dt.day)
    hour = dt.strftime('%I').lstrip('0') or '12'
    minute = dt.strftime('%M')
    ampm = dt.strftime('%p').lower()
    return f'{month} {day}, {dt.year} | {hour}:{minute} {ampm}'
