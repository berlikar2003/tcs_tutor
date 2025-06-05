// Assessment System JavaScript

class Assessment {
    constructor() {
        this.currentSection = 'quant';
        this.currentQuestionIndex = 0;
        this.questions = {};
        this.answers = {};
        this.sectionTimers = {};
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
            'quant': { questions: 25, time: 25 * 60 },
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
        // Tab switch detection
        document.addEventListener('visibilitychange', () => this.handleTabSwitch());
        window.addEventListener('blur', () => this.handleTabSwitch());
        
        // Navigation buttons
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

    // 1. Group questions by topic, limit to max 3 per chapter
    data.topics.forEach(topic => {
        if (section === 'verbal' && topic.name.toLowerCase() === 'cloze') return;
        const shuffled = topic.questions.sort(() => 0.5 - Math.random());
        topicQuestionMap.set(topic.name, shuffled.slice(0, 3));
    });

    // 2. Take 1 question from each topic to guarantee coverage
    const guaranteedQuestions = [];
    for (const [topic, questions] of topicQuestionMap.entries()) {
        if (questions.length > 0) {
            const q = questions.shift(); // take one
            guaranteedQuestions.push({ ...q, topic });
        }
    }

    // 3. Fill remaining slots from extra questions (up to 2 more per topic)
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
            
            // Update button state
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
        
        // Update question number
        document.getElementById('currentQuestionNumber').textContent = this.currentQuestionIndex + 1;
        
        // Display question text
        document.getElementById('questionText').textContent = question.question;
        
        // Display options
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
        
        // Update navigation buttons
        const prevBtn = document.getElementById('prevQuestion');
        const nextBtn = document.getElementById('nextQuestion');
        const submitBtn = document.getElementById('submitSection');
        
        prevBtn.style.display = this.currentQuestionIndex === 0 ? 'none' : 'inline-block';
        
        const isLastQuestion = this.currentQuestionIndex === this.sectionLimits[this.currentSection].questions - 1;
        nextBtn.style.display = isLastQuestion ? 'none' : 'inline-block';
        submitBtn.style.display = isLastQuestion ? 'inline-block' : 'none';
    }

    selectOption(optionKey) {
        this.answers[this.currentSection][this.currentQuestionIndex] = optionKey;
        
        // Update option display
        document.querySelectorAll('.option-item').forEach(item => {
            item.classList.remove('selected');
        });
        event.target.closest('.option-item').classList.add('selected');
        
        // Update navigator
        this.updateQuestionNavigator();
    }

    confirmSubmitSection() {
        const answeredCount = Object.keys(this.answers[this.currentSection]).length;
        const totalQuestions = this.sectionLimits[this.currentSection].questions;
        
        if (answeredCount < totalQuestions) {
            const confirm = window.confirm(
                `You have answered ${answeredCount} out of ${totalQuestions} questions. ` +
                'Are you sure you want to submit this section?'
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
        const maxQuestions = this.sectionLimits[this.currentSection].questions;
        if (this.currentQuestionIndex < maxQuestions - 1) {
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
                this.submitSection(true); // Auto-submit when time is up
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
        this.stopTimer();
        
        if (autoSubmit) {
            Utils.showNotification('Time up! Section submitted automatically.', 'warning');
        }
        
        // Calculate score for current section
        const sectionScore = this.calculateSectionScore();
        
        // Move to next section or complete assessment
        const currentSectionIndex = this.sectionOrder.indexOf(this.currentSection);
        if (currentSectionIndex < this.sectionOrder.length - 1) {
            const nextSection = this.sectionOrder[currentSectionIndex + 1];
            this.startSection(nextSection);
        } else {
            await this.completeAssessment();
        }
    }

    calculateSectionScore() {
        const questions = this.questions[this.currentSection];
        const answers = this.answers[this.currentSection];
        let correct = 0;
        
        questions.forEach((question, index) => {
            if (answers[index] === question.correct_option) {
                correct++;
            }
        });
        
        return correct;
    }

    async completeAssessment() {
        // Calculate total scores and topic-wise performance
        const results = this.calculateFinalResults();
        
        try {
            const response = await fetch('/submit_assessment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
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
                    auto_submitted: this.tabSwitchCount >= this.maxTabSwitches
                })
            });
            
            const data = await response.json();
            if (data.success) {
                // Show completion screen
                document.getElementById('assessmentInterface').style.display = 'none';
                document.getElementById('assessmentComplete').style.display = 'block';
                
                // Setup results view button
                document.getElementById('viewResults').onclick = () => {
                    window.location.href = `/assessment_results/${data.assessment_id}`;
                };
            }
        } catch (error) {
            console.error('Error submitting assessment:', error);
            Utils.showNotification('Error submitting assessment. Please try again.', 'danger');
        }
    }

    calculateFinalResults() {
        const scores = {};
        const topicStats = {};
        
        this.sectionOrder.forEach(section => {
            const questions = this.questions[section];
            const answers = this.answers[section];
            const sectionTopicStats = {};
            
            let correct = 0;
            questions.forEach((question, index) => {
                const topic = question.topic || 'Unknown';
                if (!sectionTopicStats[topic]) {
                    sectionTopicStats[topic] = { correct: 0, total: 0 };
                }
                
                sectionTopicStats[topic].total++;
                if (answers[index] === question.correct_option) {
                    correct++;
                    sectionTopicStats[topic].correct++;
                }
            });
            
            scores[section] = correct;
            topicStats[section] = sectionTopicStats;
        });
        
        const totalScore = scores.quant + scores.verbal + scores.reasoning;
        
        return { scores, topicStats, totalScore };
    }

    handleTabSwitch() {
        if (document.hidden) {
            this.tabSwitchCount++;
            document.getElementById('tabSwitchCount').textContent = this.tabSwitchCount;
            
            Utils.showNotification(
                `Warning: Tab switch detected (${this.tabSwitchCount}/${this.maxTabSwitches})`,
                'warning'
            );
            
            if (this.tabSwitchCount >= this.maxTabSwitches) {
                Utils.showNotification(
                    'Maximum tab switches exceeded. Assessment will be auto-submitted.',
                    'danger'
                );
                setTimeout(() => this.submitSection(true), 2000);
            }
        }
    }
}

// Initialize assessment when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('assessmentContainer')) {
        // Assessment will be initialized after proctoring setup
        window.assessmentInstance = null;
    }
});

// Start assessment after proctoring is enabled
function startAssessment() {
    document.getElementById('proctoringSetup').style.display = 'none';
    document.getElementById('assessmentInterface').style.display = 'block';
    
    window.assessmentInstance = new Assessment();
}

// Export for external use
window.Assessment = Assessment;
window.startAssessment = startAssessment;
