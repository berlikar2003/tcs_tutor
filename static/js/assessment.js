// Assessment System JavaScript

class Assessment {
    constructor() {
        this.currentSection = 'quant';
        this.currentQuestionIndex = 0;
        this.questions = {};
        this.answers = {};
        this.sectionTimers = {};  // ✅ New: store time used per section
        this.timeRemaining = 0;
        this.timer = null;
        this.tabSwitchCount = 0;
        this.maxTabSwitches = 3;
        this.sectionOrder = ['quant', 'verbal', 'reasoning'];
        this.sectionNames = {
            'quant': 'Quantitative Reasoning',
            'verbal': 'Verbal Ability', 
            'reasoning': 'Reasoning Ability'
        };
        this.sectionLimits = {
            'quant': { questions: 20, time: 25 * 60 },
            'verbal': { questions: 25, time: 25 * 60 },
            'reasoning': { questions: 20, time: 25 * 60 }
        };

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadQuestions();
    }

    setupEventListeners() {
        document.addEventListener('visibilitychange', () => this.handleTabSwitch());
        window.addEventListener('blur', () => this.handleTabSwitch());

        document.getElementById('prevQuestion')?.addEventListener('click', () => this.previousQuestion());
        document.getElementById('nextQuestion')?.addEventListener('click', () => this.nextQuestion());
        document.getElementById('submitSection')?.addEventListener('click', () => this.submitSection());
        document.getElementById('submitSectionEarly')?.addEventListener('click', () => this.confirmSubmitSection());
    }

    async loadQuestions() {
        try {
            const sections = ['quant', 'verbal', 'reasoning'];
            for (const section of sections) {
                const response = await fetch(`/get_questions/${section}`);
                const data = await response.json();
                this.questions[section] = this.selectRandomQuestions(data, section);
                this.answers[section] = {};
            }
            this.startSection('quant');
        } catch (error) {
            console.error('Error loading questions:', error);
            Utils.showNotification('Error loading questions. Please refresh and try again.', 'danger');
        }
    }

    selectRandomQuestions(data, section) {
        const limit = this.sectionLimits[section].questions;
        const topicQuestionMap = new Map();

        data.topics.forEach(topic => {
            if (section === 'verbal' && topic.name.toLowerCase() === 'cloze') return;
            const shuffled = topic.questions.sort(() => 0.5 - Math.random());
            topicQuestionMap.set(topic.name, shuffled.slice(0, 3));
        });

        const guaranteedQuestions = [];
        for (const [topic, questions] of topicQuestionMap.entries()) {
            if (questions.length > 0) {
                const q = questions.shift();
                guaranteedQuestions.push({ ...q, topic });
            }
        }

        const remainingSlots = limit - guaranteedQuestions.length;
        const extraPool = [];

        for (const [topic, questions] of topicQuestionMap.entries()) {
            questions.forEach(q => {
                extraPool.push({ ...q, topic });
            });
        }

        const shuffledExtras = extraPool.sort(() => 0.5 - Math.random());
        const finalExtras = shuffledExtras.slice(0, remainingSlots);

        return guaranteedQuestions.concat(finalExtras);
    }

    startSection(sectionName) {
        this.currentSection = sectionName;
        this.currentQuestionIndex = 0;
        this.timeRemaining = this.sectionLimits[sectionName].time;

        this.updateSectionHeader();
        this.updateQuestionNavigator();
        this.displayQuestion();
        this.startTimer();
    }

    updateSectionHeader() {
        document.getElementById('currentSection').textContent = this.sectionNames[this.currentSection];
        document.getElementById('totalQuestions').textContent = this.sectionLimits[this.currentSection].questions;
    }

    updateQuestionNavigator() {
        const navigator = document.getElementById('questionNavigator');
        navigator.innerHTML = '';

        const questionLimit = this.sectionLimits[this.currentSection].questions;

        for (let i = 0; i < questionLimit; i++) {
            const button = document.createElement('button');
            button.className = 'question-nav-btn';
            button.textContent = i + 1;
            button.onclick = () => this.goToQuestion(i);

            if (i === this.currentQuestionIndex) {
                button.classList.add('current');
            } else if (this.answers[this.currentSection][i]) {
                button.classList.add('answered');
            }

            navigator.appendChild(button);
        }
    }

    displayQuestion() {
        const questions = this.questions[this.currentSection];
        const question = questions[this.currentQuestionIndex];
        if (!question) return;

        document.getElementById('currentQuestionNumber').textContent = this.currentQuestionIndex + 1;
        document.getElementById('questionText').textContent = question.question;

        const optionsContainer = document.getElementById('optionsContainer');
        optionsContainer.innerHTML = '';

        Object.keys(question.options).forEach(optionKey => {
            const optionDiv = document.createElement('div');
            optionDiv.className = 'option-item';
            optionDiv.onclick = () => this.selectOption(optionKey);

            const selectedAnswer = this.answers[this.currentSection][this.currentQuestionIndex];
            if (selectedAnswer === optionKey) {
                optionDiv.classList.add('selected');
            }

            optionDiv.innerHTML = `
                <span class="option-label">${optionKey}.</span>
                ${question.options[optionKey]}
            `;

            optionsContainer.appendChild(optionDiv);
        });

        const prevBtn = document.getElementById('prevQuestion');
        const nextBtn = document.getElementById('nextQuestion');
        const submitBtn = document.getElementById('submitSection');

        prevBtn.style.display = this.currentQuestionIndex === 0 ? 'none' : 'inline-block';
        const isLast = this.currentQuestionIndex === this.sectionLimits[this.currentSection].questions - 1;
        nextBtn.style.display = isLast ? 'none' : 'inline-block';
        submitBtn.style.display = isLast ? 'inline-block' : 'none';
    }

    selectOption(optionKey) {
        this.answers[this.currentSection][this.currentQuestionIndex] = optionKey;

        document.querySelectorAll('.option-item').forEach(item => {
            item.classList.remove('selected');
        });
        event.target.closest('.option-item').classList.add('selected');

        this.updateQuestionNavigator();
    }

    confirmSubmitSection() {
        const answeredCount = Object.keys(this.answers[this.currentSection]).length;
        const totalQuestions = this.sectionLimits[this.currentSection].questions;

        if (answeredCount < totalQuestions) {
            const confirm = window.confirm(
                `You have answered ${answeredCount} out of ${totalQuestions} questions. Are you sure you want to submit this section?`
            );
            if (!confirm) return;
        }

        this.submitSection();
    }

    goToQuestion(index) {
        this.currentQuestionIndex = index;
        this.displayQuestion();
        this.updateQuestionNavigator();
    }

    previousQuestion() {
        if (this.currentQuestionIndex > 0) {
            this.currentQuestionIndex--;
            this.displayQuestion();
            this.updateQuestionNavigator();
        }
    }

    nextQuestion() {
        if (this.currentQuestionIndex < this.sectionLimits[this.currentSection].questions - 1) {
            this.currentQuestionIndex++;
            this.displayQuestion();
            this.updateQuestionNavigator();
        }
    }

    startTimer() {
        this.timer = setInterval(() => {
            this.timeRemaining--;
            document.getElementById('timer').textContent = Utils.formatTime(this.timeRemaining);

            if (this.timeRemaining <= 0) {
                this.submitSection(true);  // Auto-submit
            }
        }, 1000);
    }

    stopTimer() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    async submitSection(autoSubmit = false) {
        this.sectionTimers[this.currentSection] = this.sectionLimits[this.currentSection].time - this.timeRemaining;  // ✅ Track time used
        this.stopTimer();

        if (autoSubmit) {
            Utils.showNotification('Time up! Section submitted automatically.', 'warning');
        }

        const sectionScore = this.calculateSectionScore();

        const currentIndex = this.sectionOrder.indexOf(this.currentSection);
        if (currentIndex < this.sectionOrder.length - 1) {
            const nextSection = this.sectionOrder[currentIndex + 1];
            this.startSection(nextSection);
        } else {
            await this.completeAssessment();
        }
    }

    calculateSectionScore() {
        const questions = this.questions[this.currentSection];
        const answers = this.answers[this.currentSection];
        let correct = 0;

        questions.forEach((q, i) => {
            if (answers[i] === q.correct_option) {
                correct++;
            }
        });

        return correct;
    }

    async completeAssessment() {
        const results = this.calculateFinalResults();

        const section_times = {
            "Quantitative": this.sectionTimers.quant || 0,
            "Verbal": this.sectionTimers.verbal || 0,
            "Reasoning": this.sectionTimers.reasoning || 0
        };

        try {
            const response = await fetch('/submit_assessment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    assessment_type: 'initial',
                    quant_score: results.scores.quant,
                    verbal_score: results.scores.verbal,
                    reasoning_score: results.scores.reasoning,
                    total_score: results.totalScore,
                    quant_topics: results.topicStats.quant,
                    verbal_topics: results.topicStats.verbal,
                    reasoning_topics: results.topicStats.reasoning,
                    tab_switches: this.tabSwitchCount,
                    auto_submitted: this.tabSwitchCount >= this.maxTabSwitches,
                    section_times: section_times  // ✅ Send to backend
                })
            });

            const data = await response.json();
            if (data.success) {
                document.getElementById('assessmentInterface').style.display = 'none';
                document.getElementById('assessmentComplete').style.display = 'block';
                document.getElementById('viewResults').onclick = () => {
                    window.location.href = `/assessment_results/${data.assessment_id}`;
                };
            }
        } catch (err) {
            console.error('Error submitting assessment:', err);
            Utils.showNotification('Error submitting assessment. Please try again.', 'danger');
        }
    }

    calculateFinalResults() {
        const scores = {};
        const topicStats = {};

        this.sectionOrder.forEach(section => {
            const questions = this.questions[section];
            const answers = this.answers[section];
            const stats = {};
            let correct = 0;

            questions.forEach((q, i) => {
                const topic = q.topic || 'Unknown';
                if (!stats[topic]) stats[topic] = { correct: 0, total: 0 };
                stats[topic].total++;
                if (answers[i] === q.correct_option) {
                    correct++;
                    stats[topic].correct++;
                }
            });

            scores[section] = correct;
            topicStats[section] = stats;
        });

        const totalScore = scores.quant + scores.verbal + scores.reasoning;
        return { scores, topicStats, totalScore };
    }

    handleTabSwitch() {
        if (document.hidden) {
            this.tabSwitchCount++;
            document.getElementById('tabSwitchCount').textContent = this.tabSwitchCount;
            Utils.showNotification(`Warning: Tab switch detected (${this.tabSwitchCount}/3)`, 'warning');

            if (this.tabSwitchCount >= this.maxTabSwitches) {
                Utils.showNotification('Too many tab switches. Auto-submitting.', 'danger');
                setTimeout(() => this.submitSection(true), 2000);
            }
        }
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('assessmentContainer')) {
        window.assessmentInstance = null;
    }
});

function startAssessment() {
    document.getElementById('proctoringSetup').style.display = 'none';
    document.getElementById('assessmentInterface').style.display = 'block';
    window.assessmentInstance = new Assessment();
}

window.Assessment = Assessment;
window.startAssessment = startAssessment;
