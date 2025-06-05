import json
import os
import requests
from flask import Blueprint, request, jsonify
from ai_model import get_chatbot_response
from flask import render_template, request, redirect, url_for, session, flash, jsonify
from app import app, db
from models import User, Assessment, Progress
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask import render_template_string

bp = Blueprint('main', __name__)



@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']
        branch = request.form['branch']
        year_of_passing = int(request.form['year_of_passing'])
        age = int(request.form['age'])
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register.html')
        
        # Check if user exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(
            name=name,
            surname=surname,
            email=email,
            branch=branch,
            year_of_passing=year_of_passing,
            age=age
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = f"{user.name} {user.surname}"
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    # 🔒 Check if user exists in DB
    if not user:
        # Optionally clear session if invalid
        session.pop('user_id', None)
        return redirect(url_for('login'))

    # ✅ Now safe to access properties
    if not user.has_taken_initial_assessment:
        return redirect(url_for('initial_assessment'))

    # Get user's progress and assessments
    assessments = Assessment.query.filter_by(user_id=user.id).all()
    progress_data = Progress.query.filter_by(user_id=user.id).all()
    
    # Calculate progress statistics
    progress_stats = {
        'quant': {'completed': 0, 'total': 0},
        'verbal': {'completed': 0, 'total': 0},
        'reasoning': {'completed': 0, 'total': 0}
    }
    
    for progress in progress_data:
        if progress.subject in progress_stats:
            progress_stats[progress.subject]['completed'] += 1
            progress_stats[progress.subject]['total'] += 1
    
    return render_template('dashboard.html', user=user, assessments=assessments, progress_stats=progress_stats)

@app.route('/initial_assessment')
def initial_assessment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user.has_taken_initial_assessment:
        return redirect(url_for('dashboard'))
    
    return render_template('assessment.html', assessment_type='initial')

@app.route('/submit_assessment', methods=['POST'])
def submit_assessment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    data = request.get_json()
    user_id = session['user_id']
    
    # Create assessment record
    assessment = Assessment(
        user_id=user_id,
        assessment_type=data['assessment_type'],
        quant_score=data['quant_score'],
        verbal_score=data['verbal_score'],
        reasoning_score=data['reasoning_score'],
        total_score=data['total_score'],
        quant_topics=json.dumps(data['quant_topics']),
        verbal_topics=json.dumps(data['verbal_topics']),
        reasoning_topics=json.dumps(data['reasoning_topics']),
        tab_switches=data.get('tab_switches', 0),
        auto_submitted=data.get('auto_submitted', False)
    )
    
    db.session.add(assessment)
    
    # Mark user as having taken initial assessment
    if data['assessment_type'] == 'initial':
        user = User.query.get(user_id)
        user.has_taken_initial_assessment = True
    
    db.session.commit()
    
    return jsonify({'success': True, 'assessment_id': assessment.id})

@app.route('/assessment_results/<int:assessment_id>')
def assessment_results(assessment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    assessment = Assessment.query.get_or_404(assessment_id)
    
    # Parse topic performance
    quant_topics = json.loads(assessment.quant_topics) if assessment.quant_topics else {}
    verbal_topics = json.loads(assessment.verbal_topics) if assessment.verbal_topics else {}
    reasoning_topics = json.loads(assessment.reasoning_topics) if assessment.reasoning_topics else {}
    
    # Analyze strong and weak topics
    strong_topics = []
    weak_topics = []
    
    for subject_topics, subject_name in [
        (quant_topics, 'Quantitative'),
        (verbal_topics, 'Verbal'),
        (reasoning_topics, 'Reasoning')
    ]:
        for topic, stats in subject_topics.items():
            if stats['correct'] > 0:
                strong_topics.append(f"{subject_name}: {topic}")
            if stats['correct'] == 0 and stats['total'] > 0:
                weak_topics.append(f"{subject_name}: {topic}")
    
    return render_template('assessment_results.html', 
                         assessment=assessment, 
                         strong_topics=strong_topics, 
                         weak_topics=weak_topics)

@app.route('/subject/<subject_name>')
def subject_page(subject_name):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        from data_fetcher import DataFetcher, load_fallback_data
        
        # Map subject names
        subject_map = {
            'quantitative': 'quant',
            'verbal': 'verbal',
            'reasoning': 'reasoning'
        }
        
        subject_key = subject_map.get(subject_name)
        if not subject_key:
            return redirect(url_for('dashboard'))
        
        # Try new data structure first
        fetcher = DataFetcher()
        chapters = fetcher.get_available_chapters(subject_key)
        
        if chapters:
            # Use chapters from new structure
            topics = chapters
        else:
            # Fallback to existing JSON files
            fallback_data = load_fallback_data()
            if subject_key in fallback_data:
                topics = [topic['name'] for topic in fallback_data[subject_key]['topics']]
            else:
                topics = []
        
        return render_template('subject.html', subject_name=subject_name, topics=topics)
        
    except Exception as e:
        flash(f'Error loading subject data: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/chapter/<subject_name>/<chapter_name>')
def chapter_page(subject_name, chapter_name):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('chapter.html', subject_name=subject_name, chapter_name=chapter_name)

@app.route('/practice/<subject_name>/<chapter_name>/<level>')
def practice_page(subject_name, chapter_name, level):
    """Practice page for basic, advanced, or test questions"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Validate level
    valid_levels = ['basic', 'advanced', 'test']
    if level not in valid_levels:
        flash('Invalid practice level', 'error')
        return redirect(url_for('chapter_page', subject_name=subject_name, chapter_name=chapter_name))
    
    return render_template('practice.html', 
                         subject_name=subject_name, 
                         chapter_name=chapter_name, 
                         level=level)

@app.route('/get_chapter_questions/<subject>/<chapter>/<level>')
def get_chapter_questions(subject, chapter, level):
    """API endpoint to get questions for a specific chapter and level"""
    try:
        from data_fetcher import DataFetcher
        
        # Map subject names
        subject_map = {
            'quantitative': 'quant',
            'verbal': 'verbal',
            'reasoning': 'reasoning'
        }
        
        subject_key = subject_map.get(subject, subject)
        fetcher = DataFetcher()
        
        # Load chapter data
        chapter_data = fetcher.load_chapter_data(subject_key, chapter)
        
        if level in chapter_data:
            questions = fetcher.convert_to_assessment_format(chapter_data[level])
            return jsonify({
                "subject": subject.title(),
                "chapter": chapter,
                "level": level,
                "questions": questions
            })
        else:
            return jsonify({'error': f'No {level} questions found for {chapter}'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_questions/<subject>')
def get_questions(subject):
    """API endpoint to get questions for assessment"""
    try:
        from data_fetcher import DataFetcher, load_fallback_data
        
        # Try to load from new structure first
        fetcher = DataFetcher()
        chapters = fetcher.get_available_chapters(subject)
        
        if chapters:
            # New structure available - create assessment questions
            questions = fetcher.get_random_questions(subject, "basic", 25)
            converted_questions = fetcher.convert_to_assessment_format(questions)
            
            # Group by topics
            topics = {}
            for q in converted_questions:
                topic = q["topic"]
                if topic not in topics:
                    topics[topic] = []
                topics[topic].append(q)
            
            # Format as expected by frontend
            data = {
                "subject": subject.title(),
                "topics": [{"name": topic, "questions": questions} for topic, questions in topics.items()]
            }
            return jsonify(data)
        
        else:
            # Fallback to existing JSON files
            fallback_data = load_fallback_data()
            if subject in fallback_data:
                return jsonify(fallback_data[subject])
            else:
                return jsonify({'error': 'No data available for this subject'}), 404
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Load questions from JSON at the module level so it's available for all routes
with open("questions.json") as f:
    questions = json.load(f)

@app.route('/programming')
def programming_questions():
    return render_template('programming_questions.html', questions=questions)

@app.route('/programming/<int:question_id>')
def code_editor(question_id):
    question = next((q for q in questions if q["id"] == question_id), None)
    if question is None:
        return "Question not found", 404
    return render_template('code_editor.html', question=question)

@app.route('/run_code', methods=['POST'])
def run_code():
    data = request.json
    payload = {
        "source_code": data['source_code'],
        "language_id": data['language_id'],
        "stdin": data['stdin']
    }
    headers = {
        "X-RapidAPI-Key": "f2659eb51amsh460d02dcf118d2ap17dfe0jsn03fe2cad44c6",
        "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://judge0-ce.p.rapidapi.com/submissions?base64_encoded=false&wait=true",
        json=payload, headers=headers
    )
    return jsonify(response.json())

bp = Blueprint('main', __name__)

@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_message = request.json.get("message", "")
    bot_response = get_chatbot_response(user_message)
    return jsonify({"response": bot_response})

@bp.route('/mock_test_menu')
def mock_test_menu():
    return render_template("mock_test_menu.html")




# 🧪 Route: Launch Mock Test UI
@bp.route('/mock_test')
def mock_test():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('mock_test.html')

# 📦 API to load test data
@bp.route('/api/tests/<test_id>')
def get_mock_test(test_id):
    test_path = os.path.join('tests', f'{test_id}.json')
    if not os.path.exists(test_path):
        return jsonify({'error': 'Test not found'}), 404
    with open(test_path, 'r') as f:
        test_data = json.load(f)
    return jsonify(test_data)

# 📝 Submit mock test results
@bp.route('/submit_mock_assessment', methods=['POST'])
def submit_mock_assessment():
    data = request.get_json()
    mock_id = f"mock_{uuid.uuid4().hex[:8]}"

    if 'mock_results' not in session:
        session['mock_results'] = {}
    session['mock_results'][mock_id] = data

    return jsonify({"success": True, "assessment_id": mock_id})

# 📊 Show mock test result page
@bp.route('/mock_results/<mock_id>')
def mock_results(mock_id):
    print("All stored results:", session.get('mock_results', {}))  # 🧪 debug print
    result = session.get('mock_results', {}).get(mock_id)
    if not result:
        return "Result not found", 404
    return render_template("mock_result.html", result=result)
