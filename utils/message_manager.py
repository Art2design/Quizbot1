"""
Модуль для управления сообщениями в Telegram боте
"""
from typing import Dict, Optional
from aiogram import types
from utils.logger import logger

class MessageManager:
    """
    Класс для управления сообщениями, отправленными ботом.
    Отслеживает последнее сообщение для каждого пользователя и удаляет предыдущие сообщения.
    """
    def __init__(self):
        # Словарь для хранения последнего сообщения, отправленного каждому пользователю
        # Ключ - ID пользователя, значение - объект сообщения
        self.last_messages: Dict[int, Optional[types.Message]] = {}
    
    async def send_message(self, chat_id: int, text: str, **kwargs) -> types.Message:
        """
        Отправляет новое сообщение и удаляет предыдущее
        
        Args:
            chat_id: ID чата/пользователя
            text: Текст сообщения
            **kwargs: Дополнительные параметры для метода answer
            
        Returns:
            Отправленное сообщение
        """
        # Получаем пользовательское сообщение для отправки "ответа"
        bot = kwargs.get('bot', None)
        if not bot:
            # В kwargs нет бота, значит используем контекст текущего получателя
            user_message = kwargs.pop('user_message', None)
            if not user_message:
                logger.error(f"No user_message provided for chat_id {chat_id}")
                return None
            
            # Удаляем предыдущее сообщение бота, если оно есть
            await self.delete_last_message(chat_id)
            
            # Отправляем новое сообщение
            new_message = await user_message.answer(text=text, **kwargs)
        else:
            # Удаляем предыдущее сообщение бота, если оно есть
            await self.delete_last_message(chat_id)
            
            # В kwargs есть бот, используем прямую отправку
            new_message = await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        
        # Сохраняем новое сообщение как последнее
        self.last_messages[chat_id] = new_message
        return new_message
    
    async def edit_message(self, chat_id: int, message_id: int, **kwargs) -> types.Message:
        """
        Редактирует существующее сообщение вместо отправки нового
        
        Args:
            chat_id: ID чата/пользователя
            message_id: ID сообщения для редактирования
            **kwargs: Дополнительные параметры для метода edit_text
            
        Returns:
            Отредактированное сообщение
        """
        bot = kwargs.pop('bot', None)
        if not bot:
            user_message = kwargs.pop('user_message', None)
            if not user_message:
                logger.error(f"No user_message provided for chat_id {chat_id}")
                return None
            
            # Редактируем сообщение
            try:
                edited_message = await user_message.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    **kwargs
                )
                
                # Обновляем последнее сообщение
                self.last_messages[chat_id] = edited_message
                return edited_message
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                # Если редактирование не удалось, отправляем новое сообщение
                return await self.send_message(chat_id, kwargs.get('text', ''), user_message=user_message, **kwargs)
        else:
            # Используем прямое редактирование через переданный бот
            try:
                edited_message = await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    **kwargs
                )
                
                # Обновляем последнее сообщение
                self.last_messages[chat_id] = edited_message
                return edited_message
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                # Если редактирование не удалось, отправляем новое сообщение
                return await self.send_message(chat_id, kwargs.get('text', ''), bot=bot, **kwargs)
    
    async def delete_last_message(self, chat_id: int) -> bool:
        """
        Удаляет последнее сообщение, отправленное пользователю
        
        Args:
            chat_id: ID чата/пользователя
            
        Returns:
            True если сообщение успешно удалено, иначе False
        """
        last_message = self.last_messages.get(chat_id)
        if last_message:
            try:
                await last_message.delete()
                self.last_messages[chat_id] = None
                return True
            except Exception as e:
                logger.error(f"Error deleting message for user {chat_id}: {e}")
                # В случае ошибки удаления (например, сообщение уже удалено) сбрасываем запись
                self.last_messages[chat_id] = None
                return False
        return False
    
    def get_last_message(self, chat_id: int) -> Optional[types.Message]:
        """
        Возвращает последнее сообщение пользователю
        
        Args:
            chat_id: ID чата/пользователя
            
        Returns:
            Объект сообщения или None
        """
        return self.last_messages.get(chat_id)

# Глобальный экземпляр менеджера сообщений
message_manager = MessageManager()