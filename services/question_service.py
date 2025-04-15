import json
import os
import random
from typing import List, Dict, Any
from config import config
from utils.logger import logger

class QuestionService:
    def __init__(self, use_demo_mode=False):
        # Определяем, какой файл контента использовать (демо или полная версия)
        self.content_file = config.demo_content_file if use_demo_mode else config.content_file
        self.is_demo_mode = use_demo_mode
        
        # Загружаем данные из единого файла контента
        self.content_data = self._load_content()
        
        # Проверяем формат данных и инициализируем соответственно
        # Новый формат: {"themes": {"theme_id": {"name": "Theme Name", "questions": []}}}
        # Старый формат: {"themes": [{"id": "theme_id", "name": "Theme Name", "questions": []}]}
        
        # Инициализируем словарь вопросов по темам
        self.questions_by_theme = {}
        self.themes_info = {}  # Для хранения информации о темах (имя и т.д.)
        
        # Проверяем, есть ли 'themes' в данных
        if "themes" in self.content_data:
            themes_data = self.content_data["themes"]
            
            # Определяем формат данных
            if isinstance(themes_data, dict):
                # Новый формат (словарь тем)
                for theme_id, theme_data in themes_data.items():
                    self.questions_by_theme[theme_id] = theme_data.get("questions", [])
                    self.themes_info[theme_id] = {
                        "name": theme_data.get("name", theme_id)
                    }
            elif isinstance(themes_data, list):
                # Старый формат (список тем)
                for theme in themes_data:
                    theme_id = theme.get("id", "")
                    if theme_id:
                        self.questions_by_theme[theme_id] = theme.get("questions", [])
                        self.themes_info[theme_id] = {
                            "name": theme.get("name", theme_id)
                        }
        
        # Определяем тему по умолчанию и вопросы
        self.default_theme_id = next(iter(self.questions_by_theme.keys())) if self.questions_by_theme else ""
        self.questions = self.questions_by_theme.get(self.default_theme_id, [])
        
        # Логируем информацию о загруженных вопросах
        mode_str = "demo" if use_demo_mode else "full version"
        logger.info(f"Loaded {len(self.questions)} general questions for {mode_str}")
        for theme_id, questions in self.questions_by_theme.items():
            logger.info(f"Loaded {len(questions)} questions for theme '{theme_id}' ({mode_str})")
    
    def _load_content(self) -> Dict[str, Any]:
        """
        Загружает данные из файла контента (демо или полная версия)
        """
        try:
            if os.path.exists(self.content_file):
                with open(self.content_file, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                return data
            else:
                mode_str = "demo" if self.is_demo_mode else "full version"
                logger.warning(f"{mode_str.capitalize()} content file not found: {self.content_file}")
                
                # Если демо-файл не найден, попробуем использовать полную версию как запасной вариант
                if self.is_demo_mode and os.path.exists(config.content_file):
                    logger.warning(f"Falling back to full version content file: {config.content_file}")
                    with open(config.content_file, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                    return data
                
                return {"themes": []}
        except Exception as e:
            logger.error(f"Error loading content from {self.content_file}: {str(e)}")
            return {"themes": []}

    def get_all_questions(self) -> List[Dict[str, Any]]:
        return self.questions
        
    def get_questions_by_theme(self, theme_key: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Возвращает указанное количество случайных вопросов по заданной теме
        """
        if theme_key in self.questions_by_theme and self.questions_by_theme[theme_key]:
            questions = self.questions_by_theme[theme_key].copy()
            random.shuffle(questions)
            return questions[:count]
        else:
            # Если вопросов по теме нет, возвращаем общие вопросы
            logger.warning(f"No questions found for theme {theme_key}, using general questions")
            return self.get_all_questions()[:count]

    def get_question_by_id(self, question_id: int) -> Dict[str, Any]:
        for question in self.questions:
            if question['id'] == question_id:
                return question
        return {}

    def get_tags_from_questions(self, question_ids: List[int]) -> List[str]:
        tags = set()
        for q_id in question_ids:
            question = self.get_question_by_id(q_id)
            if question:
                tags.update(question.get('tags', []))
        return list(tags)
        
    def get_tags_from_questions_list(self, questions: List[Dict[str, Any]]) -> List[str]:
        """
        Возвращает уникальные теги из списка вопросов
        """
        tags = []
        for question in questions:
            if 'tags' in question and question['tags']:
                tags.extend(question['tags'])
        return list(set(tags))  # Возвращаем только уникальные теги
