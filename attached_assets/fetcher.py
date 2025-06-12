import os
import json
import random

def load_all_questions(base_path):
    data = {}
    for folder in ["pre final quant", "pre final verbal", "pre final resoning"]:
        folder_path = os.path.join(base_path, folder)
        if os.path.isdir(folder_path):
            subject_key = folder.lower()  # Use full lowercase folder name as key
            data[subject_key] = {}
            for filename in os.listdir(folder_path):
                if filename.endswith(".json"):
                    filepath = os.path.join(folder_path, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        chapter_name = content["Chapters"][0]["Chapter Name"]
                        sections = content["Chapters"][0]["Sections"]
                        data[subject_key][chapter_name.lower()] = {
                            section["Section Name"].lower(): section["Questions"] for section in sections
                        }
    return data

def show_menu(data):
    print("\n📚 Available Subjects, Chapters & Sections:\n")
    for subject in data:
        print(f"📘 Subject Folder: {subject}")
        for chapter in data[subject]:
            print(f"  📂 Chapter: {chapter}")
            for section in data[subject][chapter]:
                print(f"    ➤ Section: {section}")
        print()

def ask_all_questions(questions):
    for question in questions:
        print(f"\n📝 Q{question['question_no']}: {question['question']}")
        for option, text in question.get("options", {}).items():
            print(f"  {option}) {text}")
        answer = input("\nYour answer (a/b/c/...): ").strip().lower()
        correct = question.get("answer", "").lower()
        if answer == correct:
            print("✅ Correct!")
        else:
            print(f"❌ Wrong. Correct answer is: {correct.upper()}")
        input("➡️ Press Enter for next question...")

def run_test(data):
    while True:
        show_menu(data)
        subject_input = input("Enter subject (Quant/Verbal/Resoning): ").strip().lower()
        subject_key = f"pre final {subject_input}"

        chapter = input("Enter chapter name (e.g., Ages): ").strip().lower()
        section = input("Enter section (Basic/Advanced/Test): ").strip().lower()

        try:
            questions = data[subject_key][chapter][section]
            ask_all_questions(questions)
        except KeyError:
            print("❌ Invalid selection. Please check your inputs.")

        again = input("\n🔁 Try another section? (y/n): ").strip().lower()
        if again != 'y':
            break

# ✅ This must point to the folder that contains 'pre final quant' etc.
base_dir = "C:/Users/Abhishek/OneDrive/Desktop/ALL DATA"
all_data = load_all_questions(base_dir)
run_test(all_data)
