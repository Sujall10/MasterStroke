from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, PasswordField, BooleanField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional



class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])

class CourseForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('math', 'Mathematics'),
        ('science', 'Science'),
        ('programming', 'Programming'),
        ('humanities', 'Humanities'),
        ('language', 'Languages')
    ])
    thumbnail = FileField('Thumbnail Image', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])

class VideoForm(FlaskForm):
    course_id = SelectField('Course', choices=[], validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    # url = StringField('Video URL', validators=[DataRequired(), URL()])
    duration = IntegerField('Duration', validators=[DataRequired()])
    video = FileField('Video', validators=[DataRequired()])
    thumbnail = FileField('Thumbnail')
    transcript = TextAreaField('Transcript')
    


class QuizForm(FlaskForm):
    video_id = SelectField('Video', coerce=int, validators=[DataRequired()])
    question = TextAreaField('Question', validators=[DataRequired()])
    options = TextAreaField('Options (JSON array format)', validators=[DataRequired()])
    correct_answer = StringField('Correct Answer', validators=[DataRequired()])

class CommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])