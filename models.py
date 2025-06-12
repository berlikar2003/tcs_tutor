from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    branch = db.Column(db.String(100), nullable=False)
    year_of_passing = db.Column(db.Integer, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    has_taken_initial_assessment = db.Column(db.Boolean, default=False)

    assessments = db.relationship('Assessment', backref='user', lazy=True)
    progress = db.relationship('Progress', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assessment_type = db.Column(db.String(50), nullable=False)

    # Scores
    quant_score = db.Column(db.Integer, default=0)
    verbal_score = db.Column(db.Integer, default=0)
    reasoning_score = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)

    # Topic-wise performance (JSON format)
    quant_topics = db.Column(db.Text)  # JSON string
    verbal_topics = db.Column(db.Text)  # JSON string
    reasoning_topics = db.Column(db.Text)  # JSON string

    # Proctoring violations
    tab_switches = db.Column(db.Integer, default=0)
    auto_submitted = db.Column(db.Boolean, default=False)

    # ✅ Section times (stored as JSON string)
    section_times = db.Column(db.Text, nullable=True)

    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=False)  # 'quant', 'verbal', 'reasoning'
    topic = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(20), nullable=False)  # 'basic', 'advanced', 'practice'
    score = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class PracticeAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    chapter = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(20), nullable=False)  # 'basic', 'advanced', 'test'
    question_index = db.Column(db.Integer, nullable=False)
    selected_option = db.Column(db.String(5), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'subject', 'chapter', 'level', 'question_index', name='unique_practice_question'),
    )

