"""
Модуль для сбора и анализа статистики использования бота
"""
import os
import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Any
import json
from config import config
from utils.logger import logger

class AnalyticsService:
    """
    Сервис для сбора и анализа метрик использования бота
    """
    
    def __init__(self):
        """
        Инициализация сервиса аналитики и создание базы данных
        """
        # Создаем директорию для данных аналитики, если не существует
        os.makedirs("analytics_data", exist_ok=True)
        
        self.db_path = "analytics_data/bot_analytics.db"
        self._init_database()
        
    def _init_database(self):
        """
        Инициализация структуры базы данных
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Создаем таблицу для активаций бота (/start)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            is_new_user BOOLEAN NOT NULL
        )
        ''')
        
        # Создаем таблицу для подписок на канал
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS channel_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL
        )
        ''')
        
        # Создаем таблицу для начала демо-тестов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS demo_initiations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL
        )
        ''')
        
        # Создаем таблицу для завершения демо-тестов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS demo_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            correct_answers INTEGER NOT NULL,
            total_questions INTEGER NOT NULL
        )
        ''')
        
        # Создаем таблицу для запросов чек-листа
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS checklist_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def log_activation(self, user_id: int):
        """
        Записывает активацию бота пользователем (команда /start)
        
        Args:
            user_id: ID пользователя
        """
        # Не записываем действия администратора
        if user_id == config.admin_id:
            logger.info(f"Skipping logging activation for admin {user_id}")
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, новый ли это пользователь
            cursor.execute("SELECT COUNT(*) FROM activations WHERE user_id = ?", (user_id,))
            is_new_user = cursor.fetchone()[0] == 0
            
            # Записываем активацию
            cursor.execute(
                "INSERT INTO activations (user_id, timestamp, is_new_user) VALUES (?, ?, ?)",
                (user_id, datetime.now(), is_new_user)
            )
            
            conn.commit()
            conn.close()
            logger.info(f"Recorded bot activation for user {user_id}")
        except Exception as e:
            logger.error(f"Error logging activation: {str(e)}")
    
    def log_channel_subscription(self, user_id: int):
        """
        Записывает подписку пользователя на канал
        
        Args:
            user_id: ID пользователя
        """
        # Не записываем действия администратора
        if user_id == config.admin_id:
            logger.info(f"Skipping logging channel subscription for admin {user_id}")
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO channel_subscriptions (user_id, timestamp) VALUES (?, ?)",
                (user_id, datetime.now())
            )
            
            conn.commit()
            conn.close()
            logger.info(f"Recorded channel subscription for user {user_id}")
        except Exception as e:
            logger.error(f"Error logging channel subscription: {str(e)}")
    
    def log_demo_initiation(self, user_id: int):
        """
        Записывает начало прохождения демо-теста
        
        Args:
            user_id: ID пользователя
        """
        # Не записываем действия администратора
        if user_id == config.admin_id:
            logger.info(f"Skipping logging demo initiation for admin {user_id}")
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO demo_initiations (user_id, timestamp) VALUES (?, ?)",
                (user_id, datetime.now())
            )
            
            conn.commit()
            conn.close()
            logger.info(f"Recorded demo test initiation for user {user_id}")
        except Exception as e:
            logger.error(f"Error logging demo initiation: {str(e)}")
    
    def log_demo_completion(self, user_id: int, correct_answers: int, total_questions: int):
        """
        Записывает завершение прохождения демо-теста
        
        Args:
            user_id: ID пользователя
            correct_answers: Количество правильных ответов
            total_questions: Общее количество вопросов
        """
        # Не записываем действия администратора
        if user_id == config.admin_id:
            logger.info(f"Skipping logging demo completion for admin {user_id}")
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO demo_completions (user_id, timestamp, correct_answers, total_questions) VALUES (?, ?, ?, ?)",
                (user_id, datetime.now(), correct_answers, total_questions)
            )
            
            conn.commit()
            conn.close()
            logger.info(f"Recorded demo test completion for user {user_id}")
        except Exception as e:
            logger.error(f"Error logging demo completion: {str(e)}")
    
    def log_checklist_request(self, user_id: int):
        """
        Записывает запрос на получение чек-листа
        
        Args:
            user_id: ID пользователя
        """
        # Не записываем действия администратора
        if user_id == config.admin_id:
            logger.info(f"Skipping logging checklist request for admin {user_id}")
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO checklist_requests (user_id, timestamp) VALUES (?, ?)",
                (user_id, datetime.now())
            )
            
            conn.commit()
            conn.close()
            logger.info(f"Recorded checklist request for user {user_id}")
        except Exception as e:
            logger.error(f"Error logging checklist request: {str(e)}")
    
    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Возвращает статистику использования бота
        
        Args:
            days: Количество дней для выборки (по умолчанию 30)
            
        Returns:
            Dict с метриками использования
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Исключаем администратора из всех запросов
            admin_filter = f"AND user_id != {config.admin_id}" if config.admin_id else ""
            
            # Активации бота (общее количество)
            cursor.execute(f"SELECT COUNT(*) as count FROM activations WHERE timestamp > ? {admin_filter}", (start_date,))
            activations = cursor.fetchone()['count']
            
            # Подписки на канал
            cursor.execute(f"SELECT COUNT(*) as count FROM channel_subscriptions WHERE timestamp > ? {admin_filter}", (start_date,))
            channel_subscriptions = cursor.fetchone()['count']
            
            # Начало демо-тестов
            cursor.execute(f"SELECT COUNT(*) as count FROM demo_initiations WHERE timestamp > ? {admin_filter}", (start_date,))
            demo_initiations = cursor.fetchone()['count']
            
            # Завершение демо-тестов
            cursor.execute(f"SELECT COUNT(*) as count FROM demo_completions WHERE timestamp > ? {admin_filter}", (start_date,))
            demo_completions = cursor.fetchone()['count']
            
            # Запросы чек-листа
            cursor.execute(f"SELECT COUNT(*) as count FROM checklist_requests WHERE timestamp > ? {admin_filter}", (start_date,))
            checklist_requests = cursor.fetchone()['count']
            
            # Средний процент правильных ответов
            cursor.execute(f"""
                SELECT AVG(correct_answers * 100.0 / total_questions) as avg_score 
                FROM demo_completions 
                WHERE timestamp > ? {admin_filter}
            """, (start_date,))
            result = cursor.fetchone()
            knowledge_retention = result['avg_score'] if result['avg_score'] is not None else 0
            
            conn.close()
            
            return {
                "activation": activations,
                "channel_subscription_rate": channel_subscriptions,
                "demo_initiation_rate": demo_initiations,
                "demo_completion_rate": demo_completions,
                "checklist_request_rate": checklist_requests,
                "knowledge_retention_score": round(knowledge_retention, 2)
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {
                "activation": 0,
                "channel_subscription_rate": 0,
                "demo_initiation_rate": 0,
                "demo_completion_rate": 0,
                "checklist_request_rate": 0,
                "knowledge_retention_score": 0
            }
    
    def format_statistics(self, stats: Dict[str, Any]) -> str:
        """
        Форматирует статистику в человекочитаемый вид
        
        Args:
            stats: Словарь со статистикой
            
        Returns:
            Строка с отформатированной статистикой
        """
        return (
            f"📊 <b>Статистика бота за последние 30 дней</b>\n\n"
            f"🔘 <b>Activation:</b> {stats['activation']}\n"
            f"👥 <b>Channel Subscription Rate:</b> {stats['channel_subscription_rate']}\n"
            f"🚀 <b>Demo Initiation Rate:</b> {stats['demo_initiation_rate']}\n"
            f"✅ <b>Demo Completion Rate:</b> {stats['demo_completion_rate']}\n"
            f"📝 <b>Checklist Request Rate:</b> {stats['checklist_request_rate']}\n"
            f"📈 <b>Knowledge Retention Score:</b> {stats['knowledge_retention_score']}%\n"
        )


# Создаем экземпляр сервиса
analytics_service = AnalyticsService()