from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='student')  # 'student' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships with cascade delete
    progress = db.relationship('Progress', backref='user', lazy='dynamic',
                              cascade='all, delete-orphan')
    attempts = db.relationship('Attempt', backref='user', lazy='dynamic',
                              cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='user', lazy='dynamic',
                              cascade='all, delete-orphan')
    
    def is_admin(self):
        return self.email == 'user1@example.com'

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)
    thumbnail = db.Column(db.String(100), nullable=True)
    instructor = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    videos = db.relationship('Video', backref='course', lazy='dynamic',
                            cascade='all, delete-orphan')
    
    def get_progress(self, user_id):
        """Calculate user's progress through this course"""
        total_videos = self.videos.count()
        if total_videos == 0:
            return 0
            
        completed_videos = Progress.query.join(Video).filter(
            Video.course_id == self.id,
            Progress.user_id == user_id,
            Progress.completed == True
        ).count()
        
        return int((completed_videos / total_videos) * 100)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)  # URL or path to video file
    transcript = db.Column(db.Text, nullable=True)
    thumbnail = db.Column(db.String(100), nullable=True)
    duration = db.Column(db.Integer, nullable=True)  # Duration in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships with cascade delete
    quizzes = db.relationship('Quiz', backref='video', lazy='dynamic',
                             cascade='all, delete-orphan')
    progress = db.relationship('Progress', backref='video', lazy='dynamic',
                              cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='video', lazy='dynamic',
                              cascade='all, delete-orphan')

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id', ondelete='CASCADE'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)  # JSON-encoded array of options
    correct_answer = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships with cascade delete
    attempts = db.relationship('Attempt', backref='quiz', lazy='dynamic',
                              cascade='all, delete-orphan')
    
    def get_options_list(self):
        """Convert stored JSON to Python list"""
        import json
        return json.loads(self.options)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id', ondelete='CASCADE'), nullable=False)
    watched_time = db.Column(db.Integer, default=0)  # Time watched in seconds
    completed = db.Column(db.Boolean, default=False)
    last_watched = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'video_id', name='uix_user_video'),
    )

class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', ondelete='CASCADE'), nullable=False)
    selected_answer = db.Column(db.String(255), nullable=False)
    correct = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id', ondelete='CASCADE'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)