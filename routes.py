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
from models import PracticeAnswer
from sqlalchemy import func
from data_fetcher import DataFetcher  # <-- adjust import path
import joblib
import uuid  # ← Add this line


try:
    model = joblib.load(os.path.join(os.path.dirname(__file__), "recommendation.pkl"))
except Exception as e:
    model = None 
    print("⚠️")




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

    section_times = json.dumps(data.get("section_times", {}))  # ✅ NEW

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
        auto_submitted=data.get('auto_submitted', False),
        section_times=section_times  # ✅ ADD THIS
    )

    db.session.add(assessment)

    if data['assessment_type'] == 'initial':
        user = User.query.get(user_id)
        user.has_taken_initial_assessment = True

    db.session.commit()

    return jsonify({'success': True, 'assessment_id': assessment.id})

def recommend_subject(quant, verbal, reasoning, times):
    """
    Recommend subject with lowest efficiency = score / time.
    """
    scores = {
        'Quantitative': quant,
        'Verbal': verbal,
        'Reasoning': reasoning
    }

    # Prevent division by zero
    efficiency = {
        subject: round(scores[subject] / max(times.get(subject, 1), 1), 4)
        for subject in scores
    }

    # 🧪 Debug log
    print("🧠 Efficiency Debug:")
    for subject, value in efficiency.items():
        print(f"  {subject}: Score = {scores[subject]}, Time = {times.get(subject, 0)} sec, Efficiency = {value}")

    recommended = min(efficiency.items(), key=lambda x: x[1])[0]
    print(f"✅ Recommended Subject: {recommended}")

    return recommended


@app.route('/assessment_results/<int:assessment_id>')
def assessment_results(assessment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    assessment = Assessment.query.get_or_404(assessment_id)

    quant_topics = json.loads(assessment.quant_topics) if assessment.quant_topics else {}
    verbal_topics = json.loads(assessment.verbal_topics) if assessment.verbal_topics else {}
    reasoning_topics = json.loads(assessment.reasoning_topics) if assessment.reasoning_topics else {}

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

    # ✅ Load and parse section_times
    section_times = json.loads(assessment.section_times or '{}')

    # ✅ New: use time-based recommendation
    recommendation = recommend_subject(
        assessment.quant_score,
        assessment.verbal_score,
        assessment.reasoning_score,
        section_times
    )

    return render_template('assessment_results.html',
                           assessment=assessment,
                           strong_topics=strong_topics,
                           weak_topics=weak_topics,
                           recommendation=recommendation)







@app.route('/subject/<subject_name>')
def subject_page(subject_name):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        from data_fetcher import DataFetcher, load_fallback_data

        subject_map = {
            'quantitative': 'quant',
            'verbal': 'verbal',
            'reasoning': 'reasoning'
        }

        subject_key = subject_map.get(subject_name)
        if not subject_key:
            return redirect(url_for('dashboard'))

        fetcher = DataFetcher()
        chapters = fetcher.get_available_chapters(subject_key)

        if chapters:
            topics = chapters
        else:
            fallback_data = load_fallback_data()
            if subject_key in fallback_data:
                topics = [topic['name'] for topic in fallback_data[subject_key]['topics']]
            else:
                topics = []

        return render_template('subject.html', subject_name=subject_name, topics=topics)

    except Exception as e:
        flash(f'Error loading subject data: {str(e)}', 'error')
        return redirect(url_for('dashboard'))











@app.route('/subject/<subject_name>/chapter/<chapter_name>')
def chapter_page(subject_name, chapter_name):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Map full subject name to short-form key
    subject_key_map = {
        'quantitative': 'quant',
        'verbal': 'verbal',
        'reasoning': 'reasoning'
    }

    subject_key = subject_key_map.get(subject_name)
    if not subject_key:
        flash('Invalid subject.', 'error')
        return redirect(url_for('dashboard'))

    folder_map = {
        'quant': 'pre final quant',
        'verbal': 'pre final verbal',
        'reasoning': 'pre final reasoning'
    }

    level_map = {
        'basic': 'Basic',
        'advanced': 'Advanced',
        'test': 'Test'
    }

    def get_total_questions(subject, chapter, level):
        base_path = 'ALL DATA'
        try:
            subject_folder = folder_map[subject]
            file_path = os.path.join(base_path, subject_folder, f"{chapter}.json")

            print(f"Looking for: {file_path}")
            print(f"Reading for level: {level_map[level]}")

            if not os.path.exists(file_path):
                print(f"[!] File not found: {file_path}")
                return 0

            with open(file_path) as f:
                data = json.load(f)
                print("Loaded JSON Keys:", data.keys())

            for ch in data.get("Chapters", []):
                print("Chapter in JSON:", ch.get("Chapter Name"))
                if ch.get("Chapter Name", "").lower() == chapter.lower():
                    for section in ch.get("Sections", []):
                        print("Section in JSON:", section.get("Section Name"))
                        if section.get("Section Name", "").lower() == level_map[level].lower():
                            print(f"✅ Found section: {level_map[level]}, Questions: {len(section.get('Questions', []))}")
                            return len(section.get("Questions", []))
            print("⚠ Chapter or section not matched.")
            return 0
        except Exception as e:
            print(f"[X] Error reading {chapter} - {level}: {e}")
            return 0

    # Calculate progress for each level
    progress = {}
    for level in ['basic', 'advanced', 'test']:
        total = get_total_questions(subject_key, chapter_name, level)
        count = db.session.query(func.count()).select_from(PracticeAnswer).filter_by(
            user_id=user_id,
            subject=subject_key,
            chapter=chapter_name,
            level=level
        ).scalar()
        percentage = round((count / total) * 100) if total else 0

        progress[level] = {
            'answered': count,
            'total': total,
            'percentage': percentage
        }

    print("📊 Final Progress:", progress)

    return render_template('chapter.html',
                           subject_name=subject_name,
                           chapter_name=chapter_name,
                           progress=progress)

@app.route('/practice/<subject_name>/<chapter_name>/<level>')
def practice_page(subject_name, chapter_name, level):
    if 'user_id' not in session:
        return redirect(url_for('login'))

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
    test_dir = os.path.join('tests')
    all_tests = []

    try:
        all_files = [f for f in os.listdir(test_dir) if f.endswith('.json')]
        for file_name in all_files:
            test_id = file_name.replace('.json', '')
            
            if not test_id.startswith("SECTIONAL_"):
                continue  # ignore non-sectional test files

            parts = test_id.split('_')
            if len(parts) < 3:
                continue

            section_code = parts[1].lower()
            number = parts[2]

            section_map = {
                'verbal': "📚 Verbal Section",
                'quant': "📐 Quantitative Section",
                'reasoning': "🧠 Reasoning Section"
            }

            if section_code not in section_map:
                continue

            all_tests.append({
                "id": test_id,
                "title": f"{section_map[section_code]} {number}",
                "description": "50 questions | 50 minutes",
                "section": section_code
            })

        # ✅ Add this line here to debug
        print("✅ Loaded test files:", [t["id"] for t in all_tests])

    except Exception as e:
        print(f"[❌] Error loading test files: {e}")

    # Group
    verbal_tests = [t for t in all_tests if t["section"] == "verbal"]
    quant_tests = [t for t in all_tests if t["section"] == "quant"]
    reasoning_tests = [t for t in all_tests if t["section"] == "reasoning"]

    return render_template("mock_test_menu.html",
                           verbal_tests=verbal_tests,
                           quant_tests=quant_tests,
                           reasoning_tests=reasoning_tests)





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






@app.route('/api/practice_answers/<subject>/<chapter>/<level>', methods=['GET'])
def get_saved_answers(subject, chapter, level):
    """Return saved practice answers and total question count from static files or fallback dynamically."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    # 1️⃣ Query answers using original subject (not subject_key!)
    answers = PracticeAnswer.query.filter_by(
        user_id=user_id,
        subject=subject,  # keep original subject here
        chapter=chapter,
        level=level
    ).all()
    answer_dict = {a.question_index: a.selected_option for a in answers}
    print("✅ Answered:", len(answer_dict))

    # 2️⃣ Normalize subject only for file path + fallback
    subject_key_map = {
        'quantitative': 'quant',
        'verbal': 'verbal',
        'reasoning': 'resoning'  # typo preserved
    }
    subject_key = subject_key_map.get(subject, subject)

    try:
        path_map = {
            'quant': 'counts/quant_question_counts.json',
            'verbal': 'counts/verbal_question_counts.json',
            'resoning': 'counts/resoning_question_counts.json'
        }
        file_path = path_map.get(subject_key)

        print("📥 Looking for question count at:", file_path)
        total_questions = 0

        if file_path and os.path.exists(file_path):
            with open(file_path) as f:
                question_data = json.load(f)
                chapter_data = question_data.get(chapter, {})
                total_questions = chapter_data.get(level, 0)

        if total_questions == 0:
            print("🔁 Falling back to DataFetcher...")
            fetcher = DataFetcher()
            fallback_data = fetcher.load_chapter_data(subject_key, chapter)
            total_questions = len(fallback_data.get(level, []))

    except Exception as e:
        print("[❌] Error loading total:", e)
        fetcher = DataFetcher()
        fallback_data = fetcher.load_chapter_data(subject_key, chapter)
        total_questions = len(fallback_data.get(level, []))

    print("📊 Total questions for", subject, "->", chapter, "[", level, "]:", total_questions)

    return jsonify({
        'answers': answer_dict,
        'total': total_questions
    })

















@app.route('/api/save_practice_answer', methods=['POST'])
def save_practice_answer():
    """Save or update a user's answer for a specific question."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        required_fields = ['subject', 'chapter', 'level', 'question_index', 'selected_option']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        answer = PracticeAnswer.query.filter_by(
            user_id=user_id,
            subject=data['subject'],
            chapter=data['chapter'],
            level=data['level'],
            question_index=data['question_index']
        ).first()

        if answer:
            answer.selected_option = data['selected_option']
        else:
            answer = PracticeAnswer(
                user_id=user_id,
                subject=data['subject'],
                chapter=data['chapter'],
                level=data['level'],
                question_index=data['question_index'],
                selected_option=data['selected_option']
            )
            db.session.add(answer)

        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/reset_practice_answers', methods=['POST'])
def reset_practice_answers():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    PracticeAnswer.query.filter_by(
        user_id=session['user_id'],
        subject=data['subject'],
        chapter=data['chapter'],
        level=data['level']
    ).delete()
    db.session.commit()
    return jsonify({'success': True})

# app.py or routes.py
def get_total_questions(subject, chapter, level):
    import os, json
    base_path = 'ALL DATA'
    folder_map = {
        'quant': 'pre final quant',
        'verbal': 'pre final verbal',
        'reasoning': 'pre final reasoning'  # fixed typo
    }
    try:
        path = os.path.join(base_path, folder_map[subject], chapter, f'{level}.json')
        with open(path) as f:
            data = json.load(f)
            return len(data)
    except:
        return 0

