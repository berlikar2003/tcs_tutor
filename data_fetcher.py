import os
import json
import random
from typing import Dict, List, Any

class DataFetcher:
    def __init__(self, base_path="ALL DATA"):
        self.base_path = base_path
        self.subject_folders = {
            "quant": "pre final quant",
            "verbal": "pre final verbal", 
            "reasoning": "pre final reasoning"
        }
    
    def load_chapter_data(self, subject: str, chapter: str) -> Dict[str, List[Any]]:
        """Load data for a specific chapter from JSON file"""
        print(f"[DEBUG] load_chapter_data called with subject='{subject}', chapter='{chapter}'")
        try:
            folder_name = self.subject_folders.get(subject)
            if not folder_name:
                print(f"[DEBUG] No folder found for subject '{subject}'")
                return {}
            
            folder_path = os.path.join(self.base_path, folder_name)
            print(f"[DEBUG] Looking in folder: {folder_path}")
            
            for filename in os.listdir(folder_path):
                if filename.endswith(".json"):
                    filepath = os.path.join(folder_path, filename)
                    print(f"[DEBUG] Opening file: {filepath}")
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        
                        for chapter_data in content.get("Chapters", []):
                            chapter_name = chapter_data.get("Chapter Name")
                            if chapter_name is None:
                                print("[WARNING] Chapter data missing 'Chapter Name'")
                                continue

                            # Safe lower comparison
                            if chapter_name and chapter and chapter_name.lower() == chapter.lower():
                                print(f"[DEBUG] Found matching chapter: {chapter_name}")
                                sections = {}
                                for section in chapter_data.get("Sections", []):
                                    section_name = section.get("Section Name")
                                    if section_name is None:
                                        print("[WARNING] Section missing 'Section Name', skipping")
                                        continue
                                    sections[section_name.lower()] = section.get("Questions", [])
                                return sections
            
            print("[DEBUG] Chapter not found in any files")
            return {}
        except Exception as e:
            print(f"[ERROR] Exception in load_chapter_data: {e}")
            return {}
    
    def get_available_chapters(self, subject: str) -> List[str]:
        """Get list of available chapters for a subject"""
        print(f"[DEBUG] get_available_chapters called for subject='{subject}'")
        try:
            folder_name = self.subject_folders.get(subject)
            if not folder_name:
                print(f"[DEBUG] No folder found for subject '{subject}'")
                return []
            
            folder_path = os.path.join(self.base_path, folder_name)
            if not os.path.exists(folder_path):
                print(f"[DEBUG] Folder path does not exist: {folder_path}")
                return []
            
            chapters = []
            for filename in os.listdir(folder_path):
                if filename.endswith(".json"):
                    filepath = os.path.join(folder_path, filename)
                    print(f"[DEBUG] Reading file for chapters: {filepath}")
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        for chapter_data in content.get("Chapters", []):
                            chapter_name = chapter_data.get("Chapter Name")
                            if chapter_name:
                                chapters.append(chapter_name)
                            else:
                                print("[WARNING] Found chapter without 'Chapter Name'")
            
            print(f"[DEBUG] Available chapters: {chapters}")
            return chapters
        except Exception as e:
            print(f"[ERROR] Exception in get_available_chapters: {e}")
            return []
    
    def get_random_questions(self, subject: str, section_type: str = "basic", count: int = 25) -> List[Dict]:
        """Get random questions from all chapters for a subject and section type"""
        print(f"[DEBUG] get_random_questions called with subject='{subject}', section_type='{section_type}', count={count}")
        try:
            all_questions = []
            chapters = self.get_available_chapters(subject)
            print(f"[DEBUG] Found chapters: {chapters}")
            
            for chapter in chapters:
                chapter_data = self.load_chapter_data(subject, chapter)
                if section_type in chapter_data:
                    for question in chapter_data[section_type]:
                        question_copy = question.copy()
                        question_copy["topic"] = chapter
                        all_questions.append(question_copy)
                else:
                    print(f"[DEBUG] Section '{section_type}' not found in chapter '{chapter}'")
            
            if len(all_questions) >= count:
                selected = random.sample(all_questions, count)
                print(f"[DEBUG] Returning {count} random questions")
                return selected
            else:
                print(f"[DEBUG] Not enough questions, returning all {len(all_questions)}")
                return all_questions
                
        except Exception as e:
            print(f"[ERROR] Exception in get_random_questions: {e}")
            return []
    
    def convert_to_assessment_format(self, questions: List[Dict]) -> List[Dict]:
        print("[DEBUG] convert_to_assessment_format called")
        converted = []
        
        for i, q in enumerate(questions):
            answer = q.get("answer", "")
            if answer is None:
                answer = ""
            converted_q = {
                "id": f"Q{i+1}",
                "question": q.get("question", ""),
                "options": q.get("options", {}),
                "correct_option": answer.lower(),
                "answer": answer.lower(),  # Keep both for compatibility
                "topic": q.get("topic", "Unknown")
            }
            converted.append(converted_q)
        
        print(f"[DEBUG] Converted {len(converted)} questions")
        return converted


# Fallback data loading function for backward compatibility
def load_fallback_data():
    print("[DEBUG] load_fallback_data called")
    fallback_files = {
        "quant": "quant_converted.json",
        "verbal": "verbal_converted.json", 
        "reasoning": "reasoning_converted.json"
    }
    
    data = {}
    for subject, filename in fallback_files.items():
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    data[subject] = content
                    print(f"[DEBUG] Loaded fallback data for {subject} from {filename}")
        except Exception as e:
            print(f"[ERROR] Error loading fallback data for {subject}: {e}")
    
    return data
