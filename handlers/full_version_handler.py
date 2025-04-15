from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Dict, Any, List
import json
import asyncio

from services.ai_service import AIService
from services.question_service import QuestionService
from services.test_service import TestService
from services.checklist_service import ChecklistService
from config import config
from utils.logger import logger
from utils.message_manager import message_manager

class FullVersionStates(StatesGroup):
    """Состояния для полной версии тестирования"""
    SELECTING_TOPIC = State()
    ANSWERING = State()
    GETTING_RESULTS = State()

class FullVersionHandler:
    def __init__(self):
        self.ai_service = AIService()
        self.question_service = QuestionService()
        self.test_service = TestService()
        self.checklist_service = ChecklistService()
        
        # Данные по пользователям и их тестам
        self.user_sessions: Dict[int, Dict[str, Any]] = {}
        
        # Количество вопросов в тесте
        self.total_questions = 10
        
        # Количество вопросов из базы данных (остальные будут сгенерированы ИИ)
        self.db_questions_count = 5
        
        logger.info("FullVersionHandler initialized")
        
    async def handle_full_version_start(self, callback_query: types.CallbackQuery, state: FSMContext = None):
        """Обработчик начала взаимодействия с полной версией"""
        user_id = callback_query.from_user.id
        
        # Проверяем авторизацию пользователя
        if not config.is_user_authorized(user_id):
            await callback_query.answer("Эта функция доступна только для авторизованных пользователей")
            
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Создаем кнопку для возврата в главное меню
            keyboard = [
                [InlineKeyboardButton(text="🔙 Начать демо-тест", callback_data="start_test")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            # Отправляем новое сообщение с HTML-форматированием и кнопкой
            unauthorized_message = await callback_query.message.answer(
                config.messages["unauthorized"],
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[user_id] = unauthorized_message
            return
            
        # Отправляем приветственное сообщение
        await callback_query.answer()
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем приветственное сообщение с HTML-форматированием
        welcome_message = await callback_query.message.answer(
            config.messages["full_version_welcome"],
            parse_mode="HTML"
        )
        
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = welcome_message
        
        # Создаем клавиатуру с темами
        buttons = []
        for key, value in config.available_topics.items():
            buttons.append([types.InlineKeyboardButton(text=value, callback_data=f"topic_{key}")])
        markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение с выбором темы
        topic_message = await callback_query.message.answer("Выберите тему для тестирования:", reply_markup=markup)
        
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = topic_message
        
        # Устанавливаем состояние выбора темы, если state передан
        if state:
            await state.set_state(FullVersionStates.SELECTING_TOPIC)
        
    async def handle_topic_selection(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обработчик выбора темы тестирования"""
        user_id = callback_query.from_user.id
        # Извлекаем ключ темы из callback_data
        callback_data = callback_query.data
        topic_key = callback_data.replace("topic_", "")
        topic_name = config.available_topics.get(topic_key, "Неизвестная тема")
        
        logger.info(f"User {user_id} selected topic {topic_key}, name: {topic_name}")
        
        await callback_query.answer(f"Выбрана тема: {topic_name}")
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем новое сообщение о подготовке теста
        preparing_message = await callback_query.message.answer(f"Подготовка теста по теме: {topic_name}...")
        
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = preparing_message
        
        # Инициализация сессии пользователя
        self.user_sessions[user_id] = {
            "topic": topic_key,
            "topic_name": topic_name,
            "current_question": 0,
            "questions": [],
            "answers": [],
            "correct_count": 0
        }
        
        # Получаем вопросы из соответствующего файла по теме
        theme_mapping = {
            "ux_ui_basics": "ux_ui_basics",
            "user_research": "user_research"
        }
        
        theme_key = theme_mapping.get(topic_key, "ux_ui_basics")  # По умолчанию используем первую тему
        
        # В полной версии всегда генерируем точно 5 тематических вопросов
        db_questions_count = 5
        db_questions = self.question_service.get_questions_by_theme(theme_key, db_questions_count)
        
        # Логируем информацию о загруженных вопросах
        logger.info(f"Загружено {len(db_questions)} вопросов по теме {theme_key}")
        
        # На первом этапе используем только вопросы из базы данных
        # Генерацию ИИ-вопросов будем делать после ответа на 5-й вопрос
        ai_questions = []
        
        # Сохраняем информацию о необходимости генерации вопросов после 5-го
        self.user_sessions[user_id]["needs_ai_questions"] = True
        self.user_sessions[user_id]["ai_questions_count"] = self.total_questions - len(db_questions)
        self.user_sessions[user_id]["topic_name"] = topic_name
        self.user_sessions[user_id]["topic_key"] = theme_key
        
        # Сохраняем теги для будущей генерации
        unique_tags = self.question_service.get_tags_from_questions_list(db_questions)
        self.user_sessions[user_id]["tags"] = unique_tags
        
        logger.info(f"Сохранены теги для будущей генерации вопросов: {', '.join(unique_tags)}")
        
        # Объединяем вопросы из базы и сгенерированные (изначально ai_questions пустой)
        all_questions = db_questions + ai_questions
        
        # Если вопросов меньше чем нужно, добавляем вопросы из другой темы
        if len(all_questions) < self.total_questions:
            logger.warning(f"Недостаточно вопросов ({len(all_questions)}), добавляем из другой темы")
            
            # Определяем ключ другой темы
            other_theme_key = "user_research" if theme_key == "ux_ui_basics" else "ux_ui_basics"
            
            # Получаем дополнительные вопросы
            additional_count = self.total_questions - len(all_questions)
            additional_questions = self.question_service.get_questions_by_theme(
                other_theme_key, additional_count
            )
            
            all_questions.extend(additional_questions)
            logger.info(f"Добавлено {len(additional_questions)} вопросов из темы {other_theme_key}")
        
        # Ограничиваем количество вопросов до total_questions
        all_questions = all_questions[:self.total_questions]
        logger.info(f"Итого подготовлено {len(all_questions)} вопросов для теста")
        
        # Сохраняем вопросы в сессии пользователя
        self.user_sessions[user_id]["questions"] = all_questions
        
        # Переход к первому вопросу
        await self._send_question(callback_query, user_id)
        
        # Устанавливаем состояние ответа на вопросы
        await state.set_state(FullVersionStates.ANSWERING)
        
    async def _send_question(self, callback_query: types.CallbackQuery, user_id: int):
        """Отправляет текущий вопрос пользователю"""
        session = self.user_sessions.get(user_id)
        if not session:
            await callback_query.message.answer("Ошибка: сессия не найдена. Пожалуйста, начните заново.")
            return
            
        current_q_idx = session["current_question"]
        
        # Проверяем, завершился ли тест
        if current_q_idx >= len(session["questions"]) or current_q_idx >= self.total_questions:
            await self._send_results(callback_query, user_id)
            return
            
        # Получаем текущий вопрос
        question = session["questions"][current_q_idx]
        
        # Формируем текст вариантов ответов, который будет частью сообщения
        options_text = ""
        for idx, opt in enumerate(question["options"]):
            options_text += f"\n<b>Вариант {idx + 1}:</b> {opt}"
        
        # Формируем текст вопроса со всеми вариантами ответов
        question_text = f"""
<b>Вопрос {current_q_idx + 1}/{min(len(session['questions']), self.total_questions)}</b>

{question['question']}

<b>Варианты ответов:</b>{options_text}
"""
        
        # Создаем клавиатуру с вариантами ответов - только номера
        buttons = []
        for idx, _ in enumerate(question["options"]):
            buttons.append([types.InlineKeyboardButton(
                text=f"Вариант {idx + 1}", 
                callback_data=f"answer_{idx}"
            )])
        markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем вопрос с вариантами ответов
        new_message = await callback_query.message.answer(question_text, reply_markup=markup, parse_mode="HTML")
        
        # Сохраняем сообщение как последнее
        message_manager.last_messages[user_id] = new_message
        
    async def handle_answer(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обработчик ответа на вопрос"""
        user_id = callback_query.from_user.id
        answer_idx = int(callback_query.data.split('_')[1])
        
        session = self.user_sessions.get(user_id)
        if not session:
            await callback_query.answer("Ошибка: сессия не найдена.")
            return
            
        current_q_idx = session["current_question"]
        question = session["questions"][current_q_idx]
        
        # Записываем ответ пользователя
        session["answers"].append({
            "question_idx": current_q_idx,
            "user_answer": answer_idx,
            "correct_answer": question["correct_answer"],
            "is_correct": answer_idx == question["correct_answer"],
            "tags": question.get("tags", [])
        })
        
        # Если ответ правильный, увеличиваем счетчик
        if answer_idx == question["correct_answer"]:
            session["correct_count"] += 1
            await callback_query.answer("Верно! ✅")
        else:
            await callback_query.answer(f"Неверно! Правильный ответ: {question['options'][question['correct_answer']]}")
        
        # Больше не нужно удалять сообщение явно, т.к. используем message_manager
        
        # Переходим к следующему вопросу
        session["current_question"] += 1
        
        # Проверяем, нужно ли генерировать AI-вопросы
        if session.get("needs_ai_questions", False) and session["current_question"] == 5:
            # Уже ответили на 5 вопросов из базы данных, теперь генерируем AI-вопросы
            
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Отправляем сообщение о генерации
            generating_message = await callback_query.message.answer("Генерация персонализированных вопросов с помощью ИИ...")
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[user_id] = generating_message
            
            try:
                # Проверяем наличие ключа API
                if not config.ai_api_key:
                    logger.error("API ключ не найден, ИИ-генерация отключена")
                    
                    # Удаляем предыдущее сообщение
                    await message_manager.delete_last_message(user_id)
                    
                    # Отправляем сообщение об ошибке
                    error_message = await callback_query.message.answer(
                        "ИИ-генерация отключена. Используем только вопросы из базы данных."
                    )
                    
                    # Сохраняем как последнее сообщение
                    message_manager.last_messages[user_id] = error_message
                else:
                    # Получаем количество вопросов для генерации
                    ai_questions_count = session.get("ai_questions_count", 5)
                    topic_name = session.get("topic_name", "UX/UI дизайн")
                    unique_tags = session.get("tags", [])
                    
                    if unique_tags:
                        tags_text = ", ".join(unique_tags)
                        logger.info(f"Генерация вопросов с тегами: {tags_text}")
                        
                        # Используем теги вместе с темой для более точной генерации вопросов
                        topic_with_tags = f"{topic_name} по следующим тегам: {tags_text}"
                        
                        ai_questions = await self.ai_service.generate_questions(
                            topic=topic_with_tags, 
                            num_questions=ai_questions_count
                        )
                        
                        # Проверяем что каждый сгенерированный вопрос содержит все необходимые ключи
                        valid_ai_questions = []
                        for q in ai_questions:
                            if all(key in q for key in ['question', 'options', 'correct_answer']):
                                # Добавляем идентификаторы к вопросам, чтобы избежать конфликтов
                                if 'id' not in q:
                                    q['id'] = f"ai_{len(valid_ai_questions)}"
                                valid_ai_questions.append(q)
                            else:
                                logger.error(f"Сгенерированный вопрос не содержит все необходимые ключи: {q}")
                        
                        # Добавляем сгенерированные вопросы в список вопросов пользователя
                        session["questions"].extend(valid_ai_questions)
                        logger.info(f"Добавлено {len(valid_ai_questions)} сгенерированных вопросов")
                        
                        # Отключаем флаг генерации, чтобы больше не генерировать
                        session["needs_ai_questions"] = False
            except Exception as e:
                logger.error(f"Error generating questions: {str(e)}")
                
                # Удаляем предыдущее сообщение
                await message_manager.delete_last_message(user_id)
                
                # Отправляем сообщение об ошибке
                error_message = await callback_query.message.answer(
                    "Произошла ошибка при генерации вопросов. Используем только вопросы из базы данных."
                )
                
                # Сохраняем как последнее сообщение
                message_manager.last_messages[user_id] = error_message
        
        # Отправляем следующий вопрос или результаты
        await self._send_question(callback_query, user_id)
        
    async def _send_results(self, callback_query: types.CallbackQuery, user_id: int):
        """Отправляет результаты теста"""
        session = self.user_sessions.get(user_id)
        if not session:
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Отправляем сообщение об ошибке
            error_message = await callback_query.message.answer("Ошибка: сессия не найдена.")
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[user_id] = error_message
            return
            
        # Формируем статистику
        total_questions = len(session["answers"])
        correct_answers = session["correct_count"]
        percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        # Собираем информацию о тегах с ошибками
        tag_errors = {}
        for answer in session["answers"]:
            if not answer["is_correct"]:
                for tag in answer["tags"]:
                    tag_errors[tag] = tag_errors.get(tag, 0) + 1
                    
        # Сортируем теги по количеству ошибок
        sorted_tags = sorted(tag_errors.items(), key=lambda x: x[1], reverse=True)
        
        # Формируем результаты теста
        result_text = f"""
📊 <b>Результаты теста по теме "{session['topic_name']}"</b>

✅ Правильных ответов: {correct_answers} из {total_questions} ({percentage:.1f}%)

"""
        
        if sorted_tags:
            result_text += "<b>Темы с ошибками:</b>\n"
            for tag, count in sorted_tags:
                result_text += f"- {tag}: {count} ошибок\n"
        else:
            result_text += "<b>Отлично! Ошибок нет.</b>"
            
        # Создаем клавиатуру с кнопками
        buttons = [
            [types.InlineKeyboardButton(text="📝 Получить персонализированный чек-лист", callback_data="full_checklist")],
            [types.InlineKeyboardButton(text="🔄 Выбрать другую тему", callback_data="full_version")],
            [types.InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="back_to_main")]
        ]
        markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Сохраняем информацию о тегах с ошибками для генерации чек-листа
        session["failed_tags"] = sorted_tags
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем результаты
        new_message = await callback_query.message.answer(result_text, reply_markup=markup, parse_mode="HTML")
        
        # Сохраняем сообщение как последнее
        message_manager.last_messages[user_id] = new_message
        
        # Сбрасываем состояние
        try:
            # Получаем текущее состояние из контекста бота
            from aiogram.fsm.context import FSMContext
            state = FSMContext(
                storage=callback_query.bot.get_current().fsm_storage,
                key=callback_query.from_user.id
            )
            await state.clear()
        except Exception as e:
            logger.error(f"Error clearing state: {str(e)}")
        
    async def handle_checklist_request(self, callback_query: types.CallbackQuery):
        """Обработчик запроса на получение персонализированного чек-листа"""
        user_id = callback_query.from_user.id
        
        # Проверяем, есть ли сессия пользователя
        session = self.user_sessions.get(user_id)
        if not session or not session.get("failed_tags"):
            # Отвечаем на callback
            await callback_query.answer("Ошибка: данные о тесте не найдены.")
            
            # Удаляем предыдущее сообщение
            await message_manager.delete_last_message(user_id)
            
            # Отправляем сообщение об ошибке
            error_message = await callback_query.message.answer("Ошибка: сессия не найдена или нет данных для чек-листа.")
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[user_id] = error_message
            return
            
        await callback_query.answer()
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение о генерации
        generating_message = await callback_query.message.answer("Генерация персонализированного чек-листа...")
        
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = generating_message
        
        # Получаем информацию о тегах с ошибками
        failed_tags = session.get("failed_tags", [])
        topic_name = session.get("topic_name", "UX/UI Дизайн")
        
        # Если нет ошибок, отправляем стандартный чек-лист
        if not failed_tags:
            standard_checklist = self.checklist_service.generate_checklist([])
            
            checklist_text = "<b>🎉 Поздравляем! У вас нет ошибок.</b>\n\n"
            checklist_text += "Вот несколько общих ресурсов для изучения:\n\n"
            
            for resource in standard_checklist["resources"][:5]:
                checklist_text += f"<b>{resource['title']}</b>\n"
                checklist_text += f"{resource['description']}\n"
                if 'url' in resource and resource['url']:
                    checklist_text += f"🔗 <a href='{resource['url']}'>{resource['url']}</a>\n"
                checklist_text += "\n"
                
            # Удаляем предыдущее сообщение (сообщение о генерации)
            await message_manager.delete_last_message(user_id)
            
            # Создаем клавиатуру с кнопками для продолжения или выбора новой темы
            buttons = [
                [types.InlineKeyboardButton(text="🔄 Продолжить тест", callback_data="continue_test")],
                [types.InlineKeyboardButton(text="📚 Выбрать другую тему", callback_data="full_version")],
                [types.InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="back_to_main")]
            ]
            markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)
            
            # Отправляем новое сообщение с чек-листом и кнопками
            new_message = await callback_query.message.answer(
                checklist_text, 
                parse_mode="HTML", 
                disable_web_page_preview=True,
                reply_markup=markup
            )
            
            # Сохраняем как последнее сообщение
            message_manager.last_messages[user_id] = new_message
            return
            
        try:
            # Генерируем персонализированный чек-лист с помощью ИИ
            ai_checklist = await self.ai_service.generate_personalized_checklist(
                failed_tags=failed_tags,
                topic=topic_name
            )
            
            # Если генерация успешна, отправляем результат
            if ai_checklist and ai_checklist.get("resources"):
                checklist_text = "<b>📝 Персонализированный чек-лист</b>\n\n"
                
                if ai_checklist.get("explanation"):
                    checklist_text += f"{ai_checklist['explanation']}\n\n"
                    
                checklist_text += "<b>Рекомендуемые ресурсы:</b>\n\n"
                
                for resource in ai_checklist["resources"]:
                    checklist_text += f"<b>{resource['title']}</b>\n"
                    checklist_text += f"{resource['description']}\n"
                    if 'url' in resource and resource['url']:
                        checklist_text += f"🔗 <a href='{resource['url']}'>{resource['url']}</a>\n"
                    checklist_text += "\n"
                    
                # Удаляем предыдущее сообщение
                await message_manager.delete_last_message(user_id)
                
                # Создаем клавиатуру с кнопками для продолжения или выбора новой темы
                buttons = [
                    [types.InlineKeyboardButton(text="🔄 Продолжить тест", callback_data="continue_test")],
                    [types.InlineKeyboardButton(text="📚 Выбрать другую тему", callback_data="full_version")],
                    [types.InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="back_to_main")]
                ]
                markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)
                
                # Отправляем новое сообщение с AI чек-листом и кнопками
                new_message = await callback_query.message.answer(
                    checklist_text, 
                    parse_mode="HTML", 
                    disable_web_page_preview=True,
                    reply_markup=markup
                )
                
                # Сохраняем как последнее сообщение
                message_manager.last_messages[user_id] = new_message
                return
        except Exception as e:
            logger.error(f"Error generating AI checklist: {str(e)}")
            
        # Если генерация не удалась, используем стандартный чек-лист
        standard_checklist = self.checklist_service.generate_checklist(failed_tags)
        
        checklist_text = "<b>📝 Персонализированный чек-лист</b>\n\n"
        checklist_text += standard_checklist.get("tags_analysis", "")
        checklist_text += "\n<b>Рекомендуемые ресурсы:</b>\n\n"
        
        for resource in standard_checklist["resources"]:
            checklist_text += f"<b>{resource['title']}</b>\n"
            checklist_text += f"{resource['description']}\n"
            if 'url' in resource and resource['url']:
                checklist_text += f"🔗 <a href='{resource['url']}'>{resource['url']}</a>\n"
            checklist_text += "\n"
            
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Создаем клавиатуру с кнопками для продолжения или выбора новой темы
        buttons = [
            [types.InlineKeyboardButton(text="🔄 Продолжить тест", callback_data="continue_test")],
            [types.InlineKeyboardButton(text="📚 Выбрать другую тему", callback_data="full_version")],
            [types.InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="back_to_main")]
        ]
        markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Отправляем новое сообщение со стандартным чек-листом и кнопками
        new_message = await callback_query.message.answer(
            checklist_text, 
            parse_mode="HTML", 
            disable_web_page_preview=True,
            reply_markup=markup
        )
        
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = new_message
        
    async def handle_continue_test(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Обработчик продолжения теста с новыми вопросами"""
        user_id = callback_query.from_user.id
        
        # Проверяем, есть ли сессия пользователя
        session = self.user_sessions.get(user_id)
        if not session:
            # Отвечаем на callback
            await callback_query.answer("Ошибка: данные о сессии не найдены.")
            
            # Перенаправляем на выбор тем
            await self.handle_full_version_start(callback_query, state)
            return
            
        # Отвечаем на callback
        await callback_query.answer("Продолжаем тест с новыми вопросами")
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение о генерации вопросов
        generating_message = await callback_query.message.answer(
            "Генерация новых персонализированных вопросов...",
            parse_mode="HTML"
        )
        
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = generating_message
        
        # Получаем текущую тему и теги
        topic_name = session.get("topic_name", "UX/UI дизайн")
        topic_key = session.get("topic_key", "ux_ui_basics")
        unique_tags = session.get("tags", [])
        
        # Сбрасываем данные для нового круга вопросов
        session["current_question"] = 0
        session["questions"] = []
        
        try:
            # Генерация новых вопросов с помощью ИИ
            if unique_tags and config.ai_api_key:
                tags_text = ", ".join(unique_tags)
                logger.info(f"Генерация новых вопросов с тегами: {tags_text}")
                
                # Используем теги вместе с темой для более точной генерации вопросов
                topic_with_tags = f"{topic_name} по следующим тегам: {tags_text}"
                
                ai_questions = await self.ai_service.generate_questions(
                    topic=topic_with_tags, 
                    num_questions=self.total_questions
                )
                
                # Проверяем что каждый сгенерированный вопрос содержит все необходимые ключи
                valid_ai_questions = []
                for q in ai_questions:
                    if all(key in q for key in ['question', 'options', 'correct_answer']):
                        # Добавляем идентификаторы к вопросам, чтобы избежать конфликтов
                        if 'id' not in q:
                            q['id'] = f"ai_{len(valid_ai_questions)}"
                        valid_ai_questions.append(q)
                    else:
                        logger.error(f"Сгенерированный вопрос не содержит все необходимые ключи: {q}")
                
                # Если удалось сгенерировать вопросы, используем их
                if valid_ai_questions:
                    session["questions"] = valid_ai_questions
                    logger.info(f"Сгенерировано {len(valid_ai_questions)} новых вопросов")
                else:
                    # Если генерация не удалась, берем вопросы из базы
                    db_questions = self.question_service.get_questions_by_theme(topic_key, self.total_questions)
                    session["questions"] = db_questions
                    logger.info(f"Не удалось сгенерировать вопросы, используем {len(db_questions)} вопросов из базы")
            else:
                # Если нет тегов или API ключа, берем вопросы из базы
                db_questions = self.question_service.get_questions_by_theme(topic_key, self.total_questions)
                session["questions"] = db_questions
                logger.info(f"Используем {len(db_questions)} вопросов из базы")
                
        except Exception as e:
            logger.error(f"Error generating new questions: {str(e)}")
            
            # В случае ошибки берем вопросы из базы
            db_questions = self.question_service.get_questions_by_theme(topic_key, self.total_questions)
            session["questions"] = db_questions
            logger.info(f"Ошибка генерации, используем {len(db_questions)} вопросов из базы")
        
        # Переход к первому вопросу нового круга
        await self._send_question(callback_query, user_id)
        
        # Устанавливаем состояние ответа на вопросы
        await state.set_state(FullVersionStates.ANSWERING)
    
    async def handle_back_to_main(self, callback_query: types.CallbackQuery):
        """Обработчик возврата в главное меню"""
        user_id = callback_query.from_user.id
        
        # Очищаем сессию пользователя
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            
        # Отвечаем на callback
        await callback_query.answer()
        
        # Отправляем приветственное сообщение с кнопкой начала теста
        buttons = [
            [types.InlineKeyboardButton(text="Начать демо-тест", callback_data="start_test")],
            [types.InlineKeyboardButton(text="Полная версия", callback_data="full_version")]
        ]
        markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем приветственное сообщение
        new_message = await callback_query.message.answer(
            config.messages["welcome"],
            reply_markup=markup
        )
        
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = new_message