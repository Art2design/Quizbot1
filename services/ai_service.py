from typing import List, Dict, Any
import aiohttp
import json
import asyncio
from config import config
from utils.logger import logger

class AIService:
    def __init__(self):
        self.api_key = config.ai_api_key
        self.api_url = config.ai_api_url
        self.model = config.ai_model

    async def generate_questions(self, topic: str, num_questions: int = 1) -> List[Dict[str, Any]]:
        """
        Генерирует вопросы по заданной теме используя aimlapi.com API
        
        Args:
            topic: тема для генерации вопросов
            num_questions: количество вопросов для генерации
            
        Returns:
            List[Dict]: список вопросов в формате:
            {
                'question': str,
                'options': List[str],
                'correct_answer': int,
                'tags': List[str]
            }
        """
        try:
            # Извлекаем только название темы без префикса "Тема X."
            real_topic = topic
            if "." in topic:
                real_topic = topic.split(".", 1)[1].strip()
            
            # Формируем промпт для модели
            prompt = f"""
            Сгенерируй {num_questions} вопрос(ов) по теме "{real_topic}" для тестирования знаний.
            
            Формат каждого вопроса:
            1. Сам вопрос
            2. 4 варианта ответа, один из которых правильный
            3. Номер правильного ответа (0-3)
            4. 2-3 тега, описывающих подтемы вопроса
            
            Ответ должен быть в формате Python-списка словарей:
            [
                {{
                    'question': 'текст вопроса',
                    'options': ['вариант 1', 'вариант 2', 'вариант 3', 'вариант 4'],
                    'correct_answer': 0,  # номер правильного ответа (0-3)
                    'tags': ['тег1', 'тег2']
                }}
            ]
            
            Важно:
            - Вопросы должны быть практическими и профессиональными
            - Варианты ответов должны быть реалистичными
            - Теги должны точно отражать подтемы вопроса
            """
            
            # Формируем данные для запроса к API
            # Для Claude модели добавляем инструкцию в начало промпта вместо system сообщения
            enhanced_prompt = "Ты - эксперт по UX/UI дизайну, создающий вопросы для тестирования.\n\n" + prompt
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": enhanced_prompt}
                ],
                "temperature": 0.7
            }
            
            # Формируем заголовки
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Отправляем запрос к API
            logger.info(f"Отправляем запрос к aimlapi.com для генерации вопросов по теме: {real_topic}")
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API Error: {response.status}, {error_text}")
                        raise ValueError(f"API Error: {response.status}")
                        
                    response_data = await response.json()
            
            # Извлекаем текст ответа
            response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"Получен ответ от aimlapi.com, длина ответа: {len(response_text)}")
            
            # Безопасное выполнение ответа от API как Python кода
            # В реальном приложении здесь нужна дополнительная валидация
            try:
                # Извлекаем Python объект из текста ответа, заключенного в тройные кавычки, markdown блок, и пр.
                import re
                code_pattern = r'```(?:python)?(.*?)```'
                code_match = re.search(code_pattern, response_text, re.DOTALL)
                
                if code_match:
                    # Найден блок кода в markdown формате
                    code_text = code_match.group(1).strip()
                    logger.info(f"Извлечен кодовый блок из ответа: {len(code_text)} символов")
                    questions = eval(code_text)
                else:
                    # Пробуем выполнить весь текст
                    questions = eval(response_text)
                    
                # Если questions не список, преобразуем в список
                if not isinstance(questions, list):
                    logger.warning("API вернул не список. Преобразуем ответ.")
                    if isinstance(questions, dict):
                        questions = [questions]
                    else:
                        raise ValueError(f"API вернул неожиданный тип данных: {type(questions)}")
            except Exception as e:
                logger.error(f"Ошибка при парсинге ответа API: {str(e)}, текст ответа: {response_text[:100]}...")
                raise ValueError(f"Ошибка парсинга ответа API: {str(e)}")
            
            # Валидация структуры ответа
            for q in questions:
                if not all(key in q for key in ['question', 'options', 'correct_answer', 'tags']):
                    raise ValueError("Invalid question format in API response")
                if len(q['options']) != 4:
                    raise ValueError("Each question must have exactly 4 options")
                if not 0 <= q['correct_answer'] <= 3:
                    raise ValueError("Correct answer index must be between 0 and 3")
            
            logger.info(f"Успешно сгенерировано {len(questions)} вопросов")
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            # В случае ошибки возвращаем пустой список
            return []
            
    async def generate_personalized_checklist(self, failed_tags: List[tuple], topic: str) -> Dict[str, Any]:
        """
        Генерирует персонализированный чек-лист на основе результатов теста
        
        Args:
            failed_tags: список кортежей (тег, количество_ошибок)
            topic: тема тестирования
            
        Returns:
            Dict с полями:
            - resources: список рекомендованных ресурсов
            - explanation: объяснение рекомендаций
        """
        try:
            # Извлекаем только название темы без префикса "Тема X."
            real_topic = topic
            if "." in topic:
                real_topic = topic.split(".", 1)[1].strip()
            
            # Формируем текст с результатами
            tags_text = ", ".join([f"{tag} ({count} ошибок)" for tag, count in failed_tags])
            
            prompt = f"""
            На основе результатов тестирования по теме "{real_topic}" пользователь допустил ошибки в следующих областях:
            {tags_text}
            
            Сгенерируй персонализированные рекомендации, включающие:
            1. РОВНО 8 конкретных ресурсов для изучения (книги, статьи, курсы, видео)
            2. Подробное объяснение, почему эти ресурсы помогут и как они связаны с ошибками
            3. Ресурсы должны быть разнообразными: статьи, книги, видеокурсы, практические задания
            
            Формат ответа (Python dict):
            {
                'resources': [
                    {
                        'title': 'название ресурса',
                        'url': 'ссылка',
                        'description': 'подробное описание и польза'
                    },
                    ... всего 8 ресурсов
                ],
                'explanation': 'текст расширенного объяснения с анализом ошибок и рекомендациями'
            }
            """
            
            # Формируем данные для запроса к API
            # Для Claude модели добавляем инструкцию в начало промпта вместо system сообщения
            enhanced_prompt = "Ты - опытный UX/UI наставник, помогающий в обучении.\n\n" + prompt
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": enhanced_prompt}
                ],
                "temperature": 0.7
            }
            
            # Формируем заголовки
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Отправляем запрос к API
            logger.info(f"Отправляем запрос к aimlapi.com для генерации чек-листа по темам: {tags_text}")
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API Error: {response.status}, {error_text}")
                        raise ValueError(f"API Error: {response.status}")
                        
                    response_data = await response.json()
                    
            # Извлекаем текст ответа
            response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"Получен ответ от aimlapi.com, длина ответа: {len(response_text)}")
            
            # Безопасное выполнение ответа от API как Python кода
            try:
                # Извлекаем Python объект из текста ответа, заключенного в тройные кавычки, markdown блок, и пр.
                import re
                code_pattern = r'```(?:python)?(.*?)```'
                code_match = re.search(code_pattern, response_text, re.DOTALL)
                
                if code_match:
                    # Найден блок кода в markdown формате
                    code_text = code_match.group(1).strip()
                    logger.info(f"Извлечен кодовый блок из ответа: {len(code_text)} символов")
                    recommendations = eval(code_text)
                else:
                    # Пробуем выполнить весь текст
                    recommendations = eval(response_text)
            except Exception as e:
                logger.error(f"Ошибка при парсинге ответа API для чек-листа: {str(e)}, текст ответа: {response_text[:100]}...")
                raise ValueError(f"Ошибка парсинга ответа API: {str(e)}")
            
            # Валидация структуры ответа
            if not all(key in recommendations for key in ['resources', 'explanation']):
                raise ValueError("Invalid recommendations format in API response")
            
            logger.info(f"Успешно сгенерирован персонализированный чек-лист с {len(recommendations['resources'])} ресурсами")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating personalized checklist: {str(e)}")
            return {
                'resources': [],
                'explanation': "Извините, произошла ошибка при генерации рекомендаций."
            }