const fs = require("fs");
const readlineSync = require("readline-sync");

function getRandomQuestionsFromTopics(topics, totalNeeded) {
  let selected = [];

  for (let topic of topics) {
    const count = Math.random() < 0.5 ? 1 : 2;
    const shuffled = topic.questions.sort(() => 0.5 - Math.random());
    shuffled.slice(0, count).forEach(q => selected.push({ ...q, topic: topic.name }));
  }

  if (selected.length > totalNeeded) {
    selected = selected.sort(() => 0.5 - Math.random()).slice(0, totalNeeded);
  } else if (selected.length < totalNeeded) {
    const all = topics.flatMap(t => t.questions.map(q => ({ ...q, topic: t.name })));
    const extra = all
      .filter(q => !selected.some(s => s.id === q.id))
      .sort(() => 0.5 - Math.random())
      .slice(0, totalNeeded - selected.length);
    selected.push(...extra);
  }

  return selected;
}

function askQuestionsWithTopicStats(questions) {
  let correctCount = 0;
  const topicStats = {}; // topic -> { correct: x, total: y }

  questions.forEach((q, index) => {
    console.log(`\nQ${index + 1}: ${q.question}`);
    for (let key of Object.keys(q.options)) {
      console.log(`   ${key}. ${q.options[key]}`);
    }

    const userAnswer = readlineSync.question("Your answer (A/B/C/D): ").toUpperCase().trim();
    console.log(`Correct Answer: ${q.correct_option}`);
    console.log(`Your Answer: ${userAnswer}`);

    const isCorrect = userAnswer === q.correct_option.toUpperCase().trim();
    if (isCorrect) correctCount++;

    // Update topic-wise stats
    const topic = q.topic || "Unknown";
    if (!topicStats[topic]) topicStats[topic] = { correct: 0, total: 0 };
    topicStats[topic].total++;
    if (isCorrect) topicStats[topic].correct++;
  });

  return { correctCount, topicStats };
}

function printTopicStats(sectionName, topicStats) {
  console.log(`\n--- ${sectionName} - Topic-wise Performance ---`);
  for (let [topic, { correct, total }] of Object.entries(topicStats)) {
    console.log(`- ${topic}: ${correct} / ${total} correct`);
  }

  // Print topics with at least one correct
  const correctTopics = Object.entries(topicStats)
    .filter(([_, stats]) => stats.correct > 0)
    .map(([topic]) => topic);

  console.log(`\n✅ Topics you performed well in (${sectionName}):`);
  if (correctTopics.length > 0) {
    correctTopics.forEach(t => console.log(`- ${t}`));
  } else {
    console.log("None");
  }
}

// Load files
const quant = JSON.parse(fs.readFileSync("quant_converted.json", "utf-8"));
const reasoning = JSON.parse(fs.readFileSync("reasoning_converted.json", "utf-8"));
const verbal = JSON.parse(fs.readFileSync("verbal_converted.json", "utf-8"));

// Filter verbal
const filteredVerbalTopics = verbal.topics.filter(topic => topic.name.toLowerCase() !== "cloze");

// Generate sets
const quantSet = getRandomQuestionsFromTopics(quant.topics, 20);
const reasoningSet = getRandomQuestionsFromTopics(reasoning.topics, 20);
const verbalSet = getRandomQuestionsFromTopics(filteredVerbalTopics, 25);

// Ask & collect stats
const { correctCount: quantScore, topicStats: quantStats } = askQuestionsWithTopicStats(quantSet);
const { correctCount: verbalScore, topicStats: verbalStats } = askQuestionsWithTopicStats(verbalSet);
const { correctCount: reasoningScore, topicStats: reasoningStats } = askQuestionsWithTopicStats(reasoningSet);

// Total
const totalScore = quantScore + verbalScore + reasoningScore;

// Show results
console.log("\n\n--- Final Results ---");
console.log(`Quantitative Reasoning Score: ${quantScore} / 20`);
console.log(`Verbal Ability Score: ${verbalScore} / 25`);
console.log(`Reasoning Ability Score: ${reasoningScore} / 20`);
console.log(`Total Score: ${totalScore} / 65`);

printTopicStats("Quantitative Reasoning", quantStats);
printTopicStats("Verbal Ability", verbalStats);
printTopicStats("Reasoning Ability", reasoningStats);
