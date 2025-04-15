from typing import Dict, List, Any
from services.question_service import QuestionService
from utils.logger import logger

class TestService:
    def __init__(self):
        # Для демо-теста используем сервис вопросов с демо-контентом
        self.question_service = QuestionService(use_demo_mode=True)
        self.user_sessions: Dict[int, Dict[str, Any]] = {}
        self.user_results: Dict[int, Dict[str, Any]] = {}

    def start_test(self, user_id: int) -> Dict[str, Any]:
        # Получаем 10 случайных вопросов для демо-теста
        import random
        all_questions = self.question_service.get_all_questions()
        
        # Если количество вопросов меньше 10, берем все что есть
        if len(all_questions) <= 10:
            questions = all_questions
        else:
            # Иначе выбираем случайные 10 вопросов
            questions = random.sample(all_questions, 10)
        
        self.user_sessions[user_id] = {
            'current_question': 0,
            'questions': questions,
            'answers': [],
            'score': 0
        }
        return self.get_current_question(user_id)

    def get_current_question(self, user_id: int) -> Dict[str, Any]:
        if user_id not in self.user_sessions:
            return {}
        
        session = self.user_sessions[user_id]
        if session['current_question'] >= len(session['questions']):
            return {}
        
        return session['questions'][session['current_question']]

    def answer_question(self, user_id: int, answer: int) -> Dict[str, Any]:
        if user_id not in self.user_sessions:
            return {'error': 'No active test session'}

        session = self.user_sessions[user_id]
        
        # Проверка индекса текущего вопроса
        if session['current_question'] >= len(session['questions']):
            return {
                'error': 'No more questions',
                'next_question': None
            }
            
        current_question = session['questions'][session['current_question']]
        
        # Проверяем, что ответ находится в допустимом диапазоне
        if not 0 <= answer < len(current_question.get('options', [])):
            logger.warning(f"Invalid answer index {answer} for question {current_question['id']}")
            answer = 0  # Устанавливаем значение по умолчанию
            
        is_correct = current_question['correct_answer'] == answer
        if is_correct:
            session['score'] += 1

        session['answers'].append({
            'question_id': current_question['id'],
            'user_answer': answer,
            'is_correct': is_correct
        })
        
        session['current_question'] += 1
        
        # Проверяем, есть ли следующий вопрос
        next_question = self.get_current_question(user_id)
        
        return {
            'is_correct': is_correct,
            'next_question': next_question
        }

    def get_test_results(self, user_id: int) -> Dict[str, Any]:
        # Проверяем, есть ли уже сохраненные результаты для этого пользователя
        if user_id in self.user_results:
            return self.user_results[user_id]
            
        # Если результатов нет, но есть активная сессия, рассчитываем их
        if user_id not in self.user_sessions:
            return {'error': 'No test results found'}

        session = self.user_sessions[user_id]
        wrong_answers = [
            ans for ans in session['answers'] 
            if not ans['is_correct']
        ]
        
        wrong_question_ids = [ans['question_id'] for ans in wrong_answers]
        
        # Собираем все теги из неправильных ответов
        tag_error_counts = {}
        for q_id in wrong_question_ids:
            question = self.question_service.get_question_by_id(q_id)
            if question:
                for tag in question.get('tags', []):
                    if tag in tag_error_counts:
                        tag_error_counts[tag] += 1
                    else:
                        tag_error_counts[tag] = 1
        
        # Сортируем теги по количеству ошибок (по убыванию)
        sorted_failed_tags = sorted(
            tag_error_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Создаем объект с результатами
        results = {
            'score': session['score'],
            'total': len(session['questions']),
            'failed_tags': sorted_failed_tags
        }
        
        # Сохраняем результаты для последующего использования
        self.user_results[user_id] = results
        
        return results

    def end_test(self, user_id: int) -> None:
        # Сохраняем результаты перед удалением сессии
        if user_id in self.user_sessions and user_id not in self.user_results:
            self.get_test_results(user_id)  # Это сохранит результаты в self.user_results
            
        # Удаляем сессию
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
