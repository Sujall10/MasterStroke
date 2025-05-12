from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_wtf import FlaskForm
from wtforms import SubmitField
from datetime import datetime
from models import db, User, Course, Video, Quiz, Progress, Attempt, Comment
from forms import LoginForm, RegisterForm, CourseForm, VideoForm, QuizForm
from config import Config
from utils import allowed_file, calculate_progress
from dotenv import load_dotenv
from flask_wtf import CSRFProtect

load_dotenv()
# your-secret-key = ''

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
csrf = CSRFProtect(app)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()


# Main Routes
@app.route('/')
def index():
    courses = Course.query.order_by(Course.id.desc()).limit(6).all()
    return render_template('index.html', courses=courses)

@app.route('/courses')
def courses():
    category = request.args.get('category', None)
    if category:
        courses = Course.query.filter_by(category=category).all()
    else:
        courses = Course.query.all()
    return render_template('courses.html', courses=courses)

@app.route('/course/<int:course_id>')
def course(course_id):
    course = Course.query.get_or_404(course_id)
    videos = Video.query.filter_by(course_id=course_id).order_by(Video.id).all()
    
    # Calculate progress if user is logged in
    progress = {}
    if current_user.is_authenticated:
        for video in videos:
            video_progress = Progress.query.filter_by(
                user_id=current_user.id, 
                video_id=video.id
            ).first()
            if video_progress:
                progress[video.id] = video_progress.completed
            else:
                progress[video.id] = False
    
    return render_template('course.html', course=course, videos=videos, video_progress=progress)

@app.route('/video/<int:video_id>')
def video(video_id):
    video = Video.query.get_or_404(video_id)
    quizzes = Quiz.query.filter_by(video_id=video_id).all()
    comments = Comment.query.filter_by(video_id=video_id).order_by(Comment.timestamp.desc()).all()
    
    # Track progress if user is authenticated
    if current_user.is_authenticated:
        progress = Progress.query.filter_by(
            user_id=current_user.id,
            video_id=video.id
        ).first()
        
        if not progress:
            progress = Progress(
                user_id=current_user.id,
                video_id=video.id,
                watched_time=0,
                completed=False
            )
            db.session.add(progress)
            db.session.commit()

    return render_template('video.html', video=video, quizzes=quizzes, comments=comments, progress=progress)

@app.route('/update_progress', methods=['POST'])
@login_required
def update_progress():
    data = request.json
    video_id = data.get('video_id')
    watched_time = data.get('watched_time')
    is_completed = data.get('completed', False)
    
    progress = Progress.query.filter_by(
        user_id=current_user.id,
        video_id=video_id
    ).first()
    
    if progress:
        progress.watched_time = watched_time
        if is_completed:
            progress.completed = True
        db.session.commit()
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error'})

@app.route('/practice/<int:video_id>')
@login_required
def practice(video_id):
    video = Video.query.get_or_404(video_id)
    quizzes = Quiz.query.filter_by(video_id=video_id).all()
    return render_template('practice.html', video=video, quizzes=quizzes)

@app.route('/submit_quiz', methods=['POST'])
@login_required
def submit_quiz():
    data = request.json
    quiz_id = data.get('quiz_id')
    selected_answer = data.get('selected_answer')
    
    quiz = Quiz.query.get(quiz_id)
    is_correct = (selected_answer == quiz.correct_answer)
    
    attempt = Attempt(
        user_id=current_user.id,
        quiz_id=quiz_id,
        selected_answer=selected_answer,
        correct=is_correct
    )
    
    db.session.add(attempt)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'correct': is_correct,
        'correct_answer': quiz.correct_answer
    })

@app.route('/add_comment', methods=['POST'])
@login_required
def add_comment():
    video_id = request.form.get('video_id')
    content = request.form.get('content')
    
    if content:
        comment = Comment(
            user_id=current_user.id,
            video_id=int(video_id),
            content=content,
            timestamp=datetime.utcnow()
        )
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!')
    
    return redirect(url_for('video', video_id=video_id))

@app.route('/profile')
@login_required
def profile():
    # Get user progress across all courses
    user_progress = Progress.query.filter_by(user_id=current_user.id).all()
    video_ids = [p.video_id for p in user_progress]
    videos = Video.query.filter(Video.id.in_(video_ids)).all()
    
    # Map videos to courses
    course_progress = {}
    for video in videos:
        if video.course_id not in course_progress:
            course_progress[video.course_id] = {
                'course': Course.query.get(video.course_id),
                'total_videos': 0,
                'completed_videos': 0
            }
        
        course_progress[video.course_id]['total_videos'] += 1
        
        if next((p for p in user_progress if p.video_id == video.id and p.completed), None):
            course_progress[video.course_id]['completed_videos'] += 1
    
    # Calculate percentages
    for course_id, data in course_progress.items():
        if data['total_videos'] > 0:
            data['percentage'] = (data['completed_videos'] / data['total_videos']) * 100
        else:
            data['percentage'] = 0
    
    return render_template('profile.html', course_progress=course_progress)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return render_template('search.html', results=None)
    
    # Search in courses and videos
    courses = Course.query.filter(Course.title.ilike(f'%{query}%') | 
                                 Course.description.ilike(f'%{query}%')).all()
    
    videos = Video.query.filter(Video.title.ilike(f'%{query}%') | 
                               Video.description.ilike(f'%{query}%')).all()
    
    return render_template('search.html', query=query, courses=courses, videos=videos)

@app.route('/enroll/<int:course_id>', methods=['GET','POST'])
@login_required
def enroll(course_id):
    # Get the course or return 404 if it doesn't exist
    course = Course.query.get_or_404(course_id)

    # Get all videos for the course
    videos = Video.query.filter_by(course_id=course.id).all()

    enrolled = False  # Flag to track if any new progress entries are made

    for video in videos:
        # Check if the user already has a progress record for this video
        progress = Progress.query.filter_by(user_id=current_user.id, video_id=video.id).first()
        if not progress:
            # Create new progress entry (not completed, no watched time)
            new_progress = Progress(user_id=current_user.id, video_id=video.id)
            db.session.add(new_progress)
            enrolled = True

    if enrolled:
        db.session.commit()
        flash(f'You have successfully enrolled in "{course.title}".')
    else:
        flash('You are already enrolled in this course.')

    return redirect(url_for('course', course_id=course.id))

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid email or password')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered')
            return render_template('register.html', form=form)
        
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            name=form.name.data,
            email=form.email.data,
            password_hash=hashed_password,
            role='student'  # Default role
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

# Admin Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin():
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    # Get basic analytics
    total_users = User.query.count()
    total_courses = Course.query.count()
    total_videos = Video.query.count()
    
    # Get most watched videos
    most_watched = db.session.query(
        Video, db.func.count(Progress.id).label('view_count')
    ).join(Progress).group_by(Video.id).order_by(db.desc('view_count')).limit(5).all()
    
    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_courses=total_courses,
        total_videos=total_videos,
        most_watched=most_watched
    )

@app.route('/admin/users')
@login_required
def admin_all_users():
    if not current_user.is_admin():
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin/all_users.html', users=users)

# Remove this duplicate route since we already have admin_users route
# @app.route('/admin/users')
# @login_required
# def admin_all_users():
#     if not current_user.is_admin():
#         flash('Access denied: Admin privileges required')
#         return redirect(url_for('index'))
#     
#     users = User.query.all()
#     return render_template('admin/all_users.html', users=users)
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    try:
        # Find the user
        user = User.query.get_or_404(user_id)
        
        # Option 1: Delete related progress records first (safest approach)
        Progress.query.filter_by(user_id=user_id).delete()
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash('User and related data deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
        # Log the error for debugging
        app.logger.error(f"Error deleting user {user_id}: {str(e)}")
    
    return redirect(url_for('admin_users'))

@app.route('/admin/courses')
@login_required
def admin_all_courses():
    if not current_user.is_admin():
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    courses = Course.query.all()
    return render_template('admin/all_courses.html', courses=courses)

@app.route('/admin/videos')
@login_required
def admin_all_videos():
    if not current_user.is_admin():
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    videos = Video.query.all()
    return render_template('admin/all_videos.html', videos=videos)

@app.route('/admin/course/add', methods=['GET', 'POST'])
@login_required
def admin_add_course():
    if not current_user.is_admin():
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(
            title=form.title.data,
            description=form.description.data,
            category=form.category.data
        )
        
        if form.thumbnail.data:
            filename = secure_filename(form.thumbnail.data.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails', filename)
            form.thumbnail.data.save(filepath)
            course.thumbnail = filename
        
        db.session.add(course)
        db.session.commit()
        flash('Course added successfully!')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_course.html', form=form)

@app.route('/admin/video/add', methods=['GET', 'POST'])
@login_required
def admin_add_video():
    if not current_user.is_admin():
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    form = VideoForm()
    # Populate course choices
    form.course_id.choices = [(c.id, c.title) for c in Course.query.all()]
    
    if form.validate_on_submit():
        # Create a new Video instance
        video = Video(
            course_id=form.course_id.data,
            title=form.title.data,
            description=form.description.data,
            transcript=form.transcript.data,
            duration=form.duration.data
        )
        
        # Handle the thumbnail upload
        if form.thumbnail.data:
            filename = secure_filename(form.thumbnail.data.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails', filename)
            form.thumbnail.data.save(filepath)
            video.thumbnail = filename
        
        # Handle the video file upload
        if form.video.data:
            filename = secure_filename(form.video.data.filename)
            video_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'videos')
            
            # Ensure the directory exists
            if not os.path.exists(video_folder):
                os.makedirs(video_folder)  # Create the directory if it doesn't exist
            
            filepath = os.path.join(video_folder, filename)
            form.video.data.save(filepath)
            video.file_path = f"uploads/videos/{filename}"

        # Add the new video to the database
        db.session.add(video)
        db.session.commit()
        flash('Video added successfully!')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_video.html', form=form)

@app.route('/admin/quiz/add', methods=['GET', 'POST'])
@login_required
def admin_add_quiz():
    if not current_user.is_admin():
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    form = QuizForm()
    # Populate video choices
    form.video_id.choices = [(v.id, v.title) for v in Video.query.all()]
    
    if form.validate_on_submit():
        quiz = Quiz(
            video_id=form.video_id.data,
            question=form.question.data,
            options=form.options.data,
            correct_answer=form.correct_answer.data
        )
        
        db.session.add(quiz)
        db.session.commit()
        flash('Quiz question added successfully!')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_quiz.html', form=form)

@app.route('/admin/course/delete/<int:course_id>', methods=['POST', 'GET'])
@login_required
def admin_delete_course(course_id):
    if not current_user.is_admin():
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    course = Course.query.get_or_404(course_id)

    # Delete all videos under this course first
    videos = Video.query.filter_by(course_id=course.id).all()
    for video in videos:
        db.session.delete(video)

    # Now delete the course
    db.session.delete(course)
    db.session.commit()

    flash('Course and its videos deleted successfully!')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/video/delete/<int:video_id>', methods=['POST', 'GET'])
@login_required
def admin_delete_video(video_id):
    if not current_user.is_admin():
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    video = Video.query.get_or_404(video_id)

    db.session.delete(video)
    db.session.commit()

    flash('Video deleted successfully!')
    return redirect(url_for('admin_dashboard'))

# API Routes
@app.route('/api/courses', methods=['GET'])
def api_courses():
    courses = Course.query.all()
    return jsonify([{
        'id': c.id,
        'title': c.title,
        'description': c.description,
        'category': c.category,
        'thumbnail': c.thumbnail
    } for c in courses])

@app.route('/api/videos/<int:course_id>', methods=['GET'])
def api_videos(course_id):
    videos = Video.query.filter_by(course_id=course_id).all()
    return jsonify([{
        'id': v.id,
        'title': v.title,
        'description': v.description,
        'url': v.url,
        'duration': v.duration,
        'thumbnail': v.thumbnail
    } for v in videos])

if __name__ == '__main__':
    app.run(debug=True)