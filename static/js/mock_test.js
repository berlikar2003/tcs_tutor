class MockTest {
    constructor() {
        this.testData = null;
        this.questions = [];
        this.answers = {};
        this.currentIndex = 0;
        this.timeRemaining = 0;
        this.timer = null;

        this.init();
    }

    async init() {
        const testId = new URLSearchParams(window.location.search).get("testId");
        if (!testId) return alert("Missing test ID");

        try {
            const res = await fetch(`/api/tests/${testId}`);
            this.testData = await res.json();
            this.questions = this.flattenSections(this.testData.sections);
            this.timeRemaining = this.calculateTotalTime(this.testData.sections);
            this.render();
            this.startTimer();
        } catch (err) {
            console.error("Failed to load test:", err);
            alert("Could not load test.");
        }
    }

    flattenSections(sections) {
        return sections.flatMap(section =>
            section.questions.map(q => ({ ...q, sectionTitle: section.title }))
        );
    }

    calculateTotalTime(sections) {
        return sections.reduce((sum, sec) => sum + (sec.duration_minutes || 0), 0) * 60;
    }

    render() {
        this.renderQuestion();
        this.updateButtons();
        document.getElementById("mockTotalQuestions").textContent = this.questions.length;
    }

    renderQuestion() {
        const q = this.questions[this.currentIndex];
        if (!q) return;

        document.getElementById("mockCurrentQuestionNumber").textContent = this.currentIndex + 1;
        document.getElementById("mockCurrentSection").textContent = q.sectionTitle || "Mock Test";
        document.getElementById("mockQuestionText").textContent = q.question;

        const container = document.getElementById("mockOptionsContainer");
        container.innerHTML = "";

        Object.entries(q.options).forEach(([key, val]) => {
            const div = document.createElement("div");
            div.className = "option-item mb-2 p-2 border rounded";
            div.style.cursor = "pointer";
            div.innerHTML = `<strong>${key}.</strong> ${val}`;
            if (this.answers[this.currentIndex] === key) {
                div.classList.add("bg-light");
            }
            div.onclick = () => {
                this.answers[this.currentIndex] = key;
                this.renderQuestion(); // refresh to show selection
            };
            container.appendChild(div);
        });
    }

    updateButtons() {
        const prevBtn = document.getElementById("mockPrevQuestion");
        const nextBtn = document.getElementById("mockNextQuestion");
        const submitBtn = document.getElementById("mockSubmitTest");

        prevBtn.disabled = this.currentIndex === 0;
        nextBtn.classList.toggle("d-none", this.currentIndex === this.questions.length - 1);
        submitBtn.classList.toggle("d-none", this.currentIndex !== this.questions.length - 1);
    }

    next() {
        if (this.currentIndex < this.questions.length - 1) {
            this.currentIndex++;
            this.render();
        }
    }

    prev() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.render();
        }
    }

    startTimer() {
        const timerEl = document.getElementById("mockTimer");
        this.timer = setInterval(() => {
            this.timeRemaining--;
            const min = Math.floor(this.timeRemaining / 60);
            const sec = this.timeRemaining % 60;
            timerEl.textContent = `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
            if (this.timeRemaining <= 0) {
                clearInterval(this.timer);
                this.submit();
            }
        }, 1000);
    }

    async submit() {
        clearInterval(this.timer);

        const topicStats = {};
        let correct = 0;

        this.questions.forEach((q, i) => {
            const userAns = this.answers[i];
            const correctAns = q.correct_option;
            const topic = q.topic || "General";

            if (!topicStats[topic]) topicStats[topic] = { total: 0, correct: 0 };
            topicStats[topic].total++;
            if (userAns === correctAns) {
                correct++;
                topicStats[topic].correct++;
            }
        });

        const result = {
            assessment_type: "mock",
            total_score: correct,
            mock_topics: topicStats
        };

        try {
            const res = await fetch("/submit_mock_assessment", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(result)
            });

            const data = await res.json();
            if (data.success) {
                document.getElementById("mockTestContainer").innerHTML = `
                    <div class="text-center">
                        <h3>Test Completed</h3>
                        <p>Total Score: <strong>${correct}</strong></p>
                        <a href="/mock_results/${data.assessment_id}" class="btn btn-primary">View Results</a>
                    </div>
                `;

            } else {
                alert("Submission failed.");
            }
        } catch (err) {
            console.error("Submit error:", err);
            alert("Submission failed.");
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const test = new MockTest();
    document.getElementById("mockPrevQuestion").onclick = () => test.prev();
    document.getElementById("mockNextQuestion").onclick = () => test.next();
    document.getElementById("mockSubmitTest").onclick = () => test.submit();
});
