import os
import json
from config import Config
from models import Progress, Video

def allowed_file(filename):
    """Check if a file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.VIDEO_EXTENSIONS + ['jpg', 'jpeg', 'png']

def calculate_progress(user_id, course_id):
    """Calculate a user's progress through a course"""
    from models import Video, Progress, Course
    from flask_sqlalchemy import SQLAlchemy
    
    # Get all videos in the course
    videos = Video.query.filter_by(course_id=course_id).all()
    total_videos = len(videos)
    
    if total_videos == 0:
        return 0
    
    # Count completed videos
    completed_count = 0
    for video in videos:
        progress = Progress.query.filter_by(
            user_id=user_id,
            video_id=video.id,
            completed=True
        ).first()
        
        if progress:
            completed_count += 1
    
    # Calculate percentage
    return int((completed_count / total_videos) * 100)

def format_duration(seconds):
    """Format seconds to MM:SS or HH:MM:SS format"""
    if seconds is None:
        return "00:00"
        
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def parse_options(options_str):
    """Parse JSON string of quiz options into a Python list"""
    try:
        return json.loads(options_str)
    except json.JSONDecodeError:
        # If not valid JSON, try treating as comma-separated list
        return [opt.strip() for opt in options_str.split(',')]

def is_valid_json(json_str):
    """Check if a string is valid JSON"""
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False

def get_user_stats(user_id):
    """Get statistics about a user's learning activity"""
    from models import Progress, Attempt, Video, Course, db
    
    # Get total videos watched
    videos_watched = Progress.query.filter_by(
        user_id=user_id,
        completed=True
    ).count()
    
    # Get total quizzes attempted
    quizzes_attempted = Attempt.query.filter_by(
        user_id=user_id
    ).count()
    
    # Get quiz success rate
    if quizzes_attempted > 0:
        correct_attempts = Attempt.query.filter_by(
            user_id=user_id,
            correct=True
        ).count()
        quiz_success_rate = int((correct_attempts / quizzes_attempted) * 100)
    else:
        quiz_success_rate = 0
    
    # Get courses in progress
    courses_in_progress = db.session.query(Course.id).distinct().\
        join(Video).join(Progress).\
        filter(Progress.user_id == user_id).count()
    
    return {
        'videos_watched': videos_watched,
        'quizzes_attempted': quizzes_attempted,
        'quiz_success_rate': quiz_success_rate,
        'courses_in_progress': courses_in_progress
    }

def get_trending_courses(limit=5):
    """Get trending courses based on recent activity"""
    from models import Course, Video, Progress, db
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Get courses with most progress entries in the last 7 days
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    
    trending = db.session.query(
        Course,
        func.count(Progress.id).label('activity_count')
    ).join(Video, Video.course_id == Course.id)\
     .join(Progress, Progress.video_id == Video.id)\
     .filter(Progress.last_watched >= one_week_ago)\
     .group_by(Course.id)\
     .order_by(func.count(Progress.id).desc())\
     .limit(limit).all()
    
    return trending