from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, RadioField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Optional, Length


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class EntryForm(FlaskForm):
    subject = StringField('Subject', validators=[Optional(), Length(max=255)])
    body = TextAreaField('Entry', validators=[DataRequired()])
    security = SelectField(
        'Security',
        choices=[('public', 'Public'), ('private', 'Private')],
        default='public',
    )
    mood = StringField('Mood', validators=[Optional(), Length(max=100)])
    current_music = StringField('Current Music', validators=[Optional(), Length(max=255)])
    tags = StringField(
        'Tags',
        validators=[Optional(), Length(max=500)],
        description='Comma-separated, e.g. life, travel, coding',
    )
    submit = SubmitField('Post Entry')


_THEME_CHOICES = [
    ('dystopia', 'Dystopia (Blue)'),
    ('midnight', 'Midnight (Dark)'),
    ('forest',   'Forest (Green)'),
    ('crimson',  'Crimson (Red)'),
    ('vintage',  'Vintage (Warm)'),
]


class SettingsForm(FlaskForm):
    theme = RadioField('Theme', choices=_THEME_CHOICES, default='dystopia')
    custom_css = TextAreaField('Custom CSS', validators=[Optional()])
    submit = SubmitField('Save Settings')
