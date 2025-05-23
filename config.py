import os
from typing import Dict, Any, List

class Config:
    def __init__(self):
        # Базовые настройки бота
        self.bot_token = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
        self.content_file = "data/ux_ui_content.json"
        self.demo_content_file = "data/demo_ux_ui_content.json"  # Файл с отобранными вопросами для демо-теста
        self.log_file = "bot.log"
        
        # ID администратора бота для получения уведомлений
        self.admin_id = 764044921  # Замените на свой ID
        
        # AI API настройки (aimlapi.com)
        self.ai_api_key = os.getenv("OPENAI_API_KEY", "")  # Используем ту же переменную
        self.ai_api_url = "https://api.aimlapi.com/v1/chat/completions"
        self.ai_model = "claude-3-haiku-20240307"  # Модель от Anthropic, которая должна хорошо работать
        
        # Список разрешенных пользователей для полной версии
        self.authorized_users: List[int] = [764044921, 325878232, 379294891]  # ID пользователей с доступом к полной версии
        
        # Темы для генерации вопросов
        self.available_topics = {
            "ux_ui_basics": "Основы UX и UI. Разграничение понятий"
        }
        
        # Сообщения
        self.messages = {
            "welcome": """
<b>👋 Добро пожаловать в UX/UI тренажёр — интерактивный бот, который поможет тебе прокачать навыки в дизайне интерфейсов</b>

<b>Здесь ты можешь:</b>

• Пройти демо-тест: всего 10 коротких вопросов по основам UX/UI. По результатам ты получишь чек-лист с рекомендациями, которые помогут понять, где ты силён, а над чем стоит поработать. Отличный способ быстро оценить свой уровень

• Перейти к полной версии: это 8 ключевых тем по UX и UI, неограниченное количество вопросов и чек-листы, которые формирует ИИ специально под твои ответы. Тренажёр адаптируется под твои сильные и слабые стороны, чтобы обучение было максимально полезным и точным

<b>Быстрый старт:</b>
1. Подпишитесь на наш Telegram канал - @InterfAIceSchool
2. Нажмите «🎯 Начать демо-тест» для проверки знаний
3. После прохождения получите чек-лист с персональными ресурсами
4. Команда /start — вернуться в главное меню
5. Команда /cancel — отменить текущий тест

<b>Выберите действие:</b>
""",
            "test_complete": """
Тест завершен!
Ваш результат: {score}/{total}
Теги, в которых были ошибки: {failed_tags}
""",
            "unauthorized": """
<b>✨ Скоро открытие полной версии! ✨</b>

<b>Извините, в данный момент полная версия находится в разработке.</b> Мы создаем для вас максимально комфортную и эффективную платформу обучения!

<b>С полной версией вы сможете:</b>
• Отвечать на персонализированные вопросы, сгенерированные искусственным интеллектом
• Получать персональные чек-листы на основе ваших знаний и пробелов
• Проходить тесты по различным темам UX/UI дизайна
• Отслеживать свой прогресс и развиваться быстрее

<b>Следите за актуальными новостями в нашей группе:</b>
<a href="https://t.me/InterfAIceSchool">https://t.me/InterfAIceSchool</a>

Спасибо за ваш интерес к нашему проекту! ❤️
""",
            "full_version_welcome": """
<b>Добро пожаловать в полную версию бота!</b>

<b>Расширенные возможности:</b>
• Выбор конкретных тем для тестирования
• Вопросы, генерируемые с помощью ИИ
• Подробная статистика правильных/неправильных ответов
• Персонализированные рекомендации по темам с ошибками

<b>Выберите тему для тестирования:</b>
"""
        }
    
    def is_user_authorized(self, user_id: int) -> bool:
        """Проверяет, есть ли у пользователя доступ к полной версии"""
        # Временно отключаем доступ для всех пользователей
        return False
        
    def add_authorized_user(self, user_id: int) -> None:
        """Добавляет пользователя в список авторизованных"""
        if user_id not in self.authorized_users:
            self.authorized_users.append(user_id)

config = Config()
