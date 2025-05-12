from models import Video
from app import app, db

with app.app_context():
    video = db.session.get(Video, 1)
    print(video)

# List all videos
# videos = Video.query.all()
# for video in videos:
#     print(video.id, video.title, video.filename)

