from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.test_service import TestService
from services.checklist_service import ChecklistService
from services.analytics_service import analytics_service
from config import config
from utils.logger import logger
from utils.message_manager import message_manager

class TestStates(StatesGroup):
    ANSWERING = State()

class TestHandler:
    def __init__(self):
        self.test_service = TestService()  # TestService уже настроен на демо-режим
        self.checklist_service = ChecklistService(use_demo_mode=True)  # Используем демо-версию для чек-листов
        logger.info("TestHandler initialized")

    async def handle_start_test(self, callback_query: types.CallbackQuery):
        """
        Обработчик начала теста
        """
        try:
            user_id = callback_query.from_user.id
            logger.info(f"Starting test for user {user_id}")
            
            # Записываем в аналитику начало демо-теста
            analytics_service.log_demo_initiation(user_id)

            question = self.test_service.start_test(user_id)
            if not question:
                logger.error(f"No questions available for user {user_id}")
                
                # Удаляем предыдущее сообщение
                await message_manager.delete_last_message(user_id)
                
                # Отправляем сообщение об ошибке
                error_message = await callback_query.message.answer(
                    "К сожалению, сейчас нет доступных вопросов. Попробуйте позже."
                )
                
                # Сохраняем как последнее сообщение
                message_manager.last_messages[user_id] = error_message
                return

            await self._send_question(callback_query, question)

        except Exception as e:
            logger.error(f"Error starting test: {str(e)}")
            
            user_id = callback_query.from_user.id
            
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Отправляем сообщение об ошибке
            error_message = await callback_query.message.answer(
                "Произошла ошибка при запуске теста. Попробуйте еще раз позже."
            )
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[user_id] = error_message

    async def handle_answer(self, callback_query: types.CallbackQuery):
        """
        Обработчик ответа на вопрос
        """
        try:
            user_id = callback_query.from_user.id
            logger.info(f"Received answer from user {user_id}")

            answer_num = int(callback_query.data.split('_')[1])
            logger.info(f"User {user_id} selected answer {answer_num}")

            result = self.test_service.answer_question(user_id, answer_num)

            # Больше не нужно удалять сообщение явно, т.к. используем message_manager

            if result.get('next_question'):
                # Отправляем новое сообщение со следующим вопросом без промежуточного уведомления
                await self._send_question(callback_query, result['next_question'])
            else:
                await self._send_results(callback_query, user_id)
                self.test_service.end_test(user_id)

        except Exception as e:
            logger.error(f"Error handling answer: {str(e)}")
            
            user_id = callback_query.from_user.id
            
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Отправляем сообщение об ошибке
            error_message = await callback_query.message.answer(
                "Произошла ошибка при обработке ответа. Пожалуйста, начните тест заново с помощью команды /start"
            )
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[user_id] = error_message

    async def _send_question(self, callback_query: types.CallbackQuery, question: dict):
        """
        Отправка вопроса пользователю
        """
        if not question:
            logger.error("Attempted to send empty question")
            return

        user_id = callback_query.from_user.id

        # Создаем клавиатуру с полным текстом вариантов ответов
        keyboard = []
        for i, option in enumerate(question['options']):
            # Помещаем полный текст ответа в кнопку
            keyboard.append([InlineKeyboardButton(text=option, callback_data=f"answer_{i}")])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Получаем общее количество вопросов
        total_questions = len(self.test_service.user_sessions[user_id]['questions'])
        
        # Определяем текущий индекс вопроса (начиная с 0)
        current_index = self.test_service.user_sessions[user_id]['current_question']
        
        # ID вопроса для отображения (проверяем тип и при необходимости обрабатываем префикс)
        current_question_id = question['id']
        if isinstance(current_question_id, str) and current_question_id.startswith('demo_'):
            current_question_id = current_question_id.replace('demo_', '')
        
        # Применяем индекс текущего вопроса + 1 для отображения пользователю (начиная с 1)
        current_question_number = current_index + 1
        
        # Формируем текст вопроса без вариантов ответов
        formatted_text = f"""
<b>Вопрос {current_question_number} из {total_questions}</b>

{question['question']}
"""

        try:
            # Удаляем все предыдущие сообщения бота
            await message_manager.delete_last_message(user_id)
            
            # Отправляем новое сообщение с вопросом
            new_message = await callback_query.message.answer(
                text=formatted_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            # Сохраняем сообщение как последнее для этого пользователя
            message_manager.last_messages[user_id] = new_message
            
            logger.info(f"Sent question ID {question['id']} to user")
        except Exception as e:
            logger.error(f"Error sending question: {str(e)}")
            
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Отправляем сообщение об ошибке
            error_message = await callback_query.message.answer(
                "Произошла ошибка при отправке вопроса. Пожалуйста, начните тест заново с помощью команды /start"
            )
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[user_id] = error_message

    async def _send_results(self, callback_query: types.CallbackQuery, user_id: int):
        """
        Отправка результатов теста
        """
        try:
            logger.info(f"Sending test results to user {user_id}")
            results = self.test_service.get_test_results(user_id)
            
            # Записываем в аналитику завершение демо-теста
            analytics_service.log_demo_completion(
                user_id, 
                results['score'], 
                results['total']
            )
            
            # Получаем анализ тегов с ошибками через сервис чек-листа
            checklist_data = self.checklist_service.generate_checklist(results['failed_tags'])
            tags_analysis = checklist_data['tags_analysis']

            # Основное сообщение с результатами с HTML-форматированием
            message = f"""
<b>🎓 Тест завершен! 🎓</b>

<b>Ваш результат:</b> {results['score']}/{results['total']}

<b>Процент правильных ответов:</b> {int((results['score'] / results['total']) * 100)}%

{tags_analysis}
"""

            # Создаем одну кнопку: получить чек-лист
            keyboard = [
                [InlineKeyboardButton(text="📋 Получить чек-лист", callback_data=f"checklist_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Отправляем новое сообщение с результатами
            new_message = await callback_query.message.answer(
                text=message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            # Сохраняем сообщение как последнее
            message_manager.last_messages[user_id] = new_message
            
            logger.info(f"Test results sent to user {user_id}")

        except Exception as e:
            logger.error(f"Error sending results: {str(e)}")
            
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Отправляем сообщение об ошибке
            error_message = await callback_query.message.answer(
                "Произошла ошибка при отправке результатов. Ваши ответы были сохранены. Используйте /start для нового теста."
            )
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[user_id] = error_message
            
    async def handle_checklist(self, callback_query: types.CallbackQuery):
        """
        Обработчик запроса на получение чек-листа
        """
        try:
            user_id = int(callback_query.data.split('_')[1])
            logger.info(f"Generating checklist for user {user_id}")
            
            # Записываем в аналитику запрос на получение чек-листа
            analytics_service.log_checklist_request(user_id)
            
            # Получаем данные о тестировании пользователя
            results = self.test_service.get_test_results(user_id)
            
            # Проверяем наличие ключа 'failed_tags' в результатах
            if 'failed_tags' not in results:
                logger.error(f"Failed_tags missing in results for user {user_id}")
                logger.info(f"Results content: {results}")
                
                # Удаляем предыдущее сообщение
                await message_manager.delete_last_message(user_id)
                
                # Отправляем сообщение об ошибке
                error_message = await callback_query.message.answer(
                    "Не удалось загрузить данные о тестировании. Пожалуйста, пройдите тест заново."
                )
                
                # Сохраняем как последнее сообщение
                message_manager.last_messages[user_id] = error_message
                return
                
            # Проверяем, что failed_tags - это список
            if not isinstance(results['failed_tags'], list):
                logger.error(f"Failed_tags is not a list for user {user_id}. Type: {type(results['failed_tags'])}")
                logger.info(f"Failed_tags content: {results['failed_tags']}")
                
                # Удаляем предыдущее сообщение
                await message_manager.delete_last_message(user_id)
                
                # Отправляем сообщение об ошибке
                error_message = await callback_query.message.answer(
                    "Данные о тестировании повреждены. Пожалуйста, пройдите тест заново."
                )
                
                # Сохраняем как последнее сообщение
                message_manager.last_messages[user_id] = error_message
                return
            
            # Генерируем чек-лист на основе тегов с ошибками
            logger.info(f"Generating checklist with tags: {results['failed_tags']}")
            checklist_data = self.checklist_service.generate_checklist(results['failed_tags'])
            
            # Проверяем результат генерации чек-листа
            if not isinstance(checklist_data, dict) or 'resources' not in checklist_data:
                logger.error(f"Invalid checklist data for user {user_id}: {checklist_data}")
                
                # Удаляем предыдущее сообщение
                await message_manager.delete_last_message(user_id)
                
                # Отправляем сообщение об ошибке
                error_message = await callback_query.message.answer(
                    "Ошибка при генерации чек-листа. Пожалуйста, попробуйте позже."
                )
                
                # Сохраняем как последнее сообщение
                message_manager.last_messages[user_id] = error_message
                return
            
            resources = checklist_data['resources']
            
            if not resources:
                message = """
<b>🎉 Поздравляем! У вас не было ошибок! 🎉</b>

Вы отлично справились с тестом, поэтому у нас нет специальных рекомендаций для вас.
"""
            else:
                # Формируем сообщение с ресурсами
                resources_text = "\n\n".join([
                    f"<b>{index + 1}. <a href='{res['url']}'>{res['title']}</a></b>\n{res['description']}"
                    for index, res in enumerate(resources)
                ])
                
                message = f"""
<b>📚 Персональный чек-лист ресурсов 📚</b>

На основе ваших ответов мы подготовили рекомендации по ресурсам, которые помогут вам улучшить знания в областях, где были допущены ошибки:

{resources_text}
"""
            
            # Кнопки "Начать демо-тест заново" и "Приобрести полную версию"
            keyboard = [
                [InlineKeyboardButton(text="🔄 Начать демо-тест заново", callback_data="start_test")],
                [InlineKeyboardButton(text="✨ Полная версия 149 руб/мес", callback_data="full_version")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Отправляем новое сообщение с чек-листом
            new_message = await callback_query.message.answer(
                text=message,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=False  # Разрешаем превью для ссылок
            )
            
            # Сохраняем сообщение как последнее
            message_manager.last_messages[user_id] = new_message
            
            logger.info(f"Checklist sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending checklist: {str(e)}")
            
            # Получаем user_id из callback_query
            current_user_id = callback_query.from_user.id
            
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(current_user_id)
            
            # Отправляем сообщение об ошибке
            error_message = await callback_query.message.answer(
                "Произошла ошибка при отправке чек-листа. Пожалуйста, попробуйте еще раз позже."
            )
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[current_user_id] = error_message
            
    async def handle_full_version(self, callback_query: types.CallbackQuery):
        """
        Обработчик кнопки "Полная версия"
        """
        # Функциональность переехала в full_version_handler
        # Оставляем метод для обратной совместимости
        pass
        
    async def handle_continue_demo_test(self, callback_query: types.CallbackQuery):
        """
        Обработчик кнопки "Продолжить тест" в демо-версии.
        Генерирует новые вопросы для текущего теста.
        """
        user_id = callback_query.from_user.id
        logger.info(f"User {user_id} requested to continue demo test with new questions")
        
        try:
            # Отвечаем на callback
            await callback_query.answer("Генерация новых вопросов...")
            
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Отправляем сообщение о генерации
            preparing_message = await callback_query.message.answer(
                "Подготовка новых вопросов для продолжения теста..."
            )
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[user_id] = preparing_message
            
            # Сбрасываем состояние текущего теста, но сохраняем результаты
            self.test_service.end_test(user_id)
            
            # Запускаем новый тест
            question = self.test_service.start_test(user_id)
            
            if not question:
                logger.error(f"No questions available for user {user_id}")
                
                # Удаляем предыдущее сообщение
                await message_manager.delete_last_message(user_id)
                
                # Отправляем сообщение об ошибке
                error_message = await callback_query.message.answer(
                    "К сожалению, сейчас нет доступных вопросов. Попробуйте позже."
                )
                
                # Сохраняем как последнее сообщение
                message_manager.last_messages[user_id] = error_message
                return
                
            await self._send_question(callback_query, question)
            logger.info(f"Started continued demo test for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error continuing demo test: {str(e)}")
            
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Отправляем сообщение об ошибке
            error_message = await callback_query.message.answer(
                "Произошла ошибка при генерации новых вопросов. Пожалуйста, попробуйте позже."
            )
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[user_id] = error_message