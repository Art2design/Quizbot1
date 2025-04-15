from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
import asyncio
from datetime import datetime
from config import config
from handlers.test_handler import TestHandler
from handlers.full_version_handler import FullVersionHandler
from utils.logger import logger
from utils.message_manager import message_manager
from services.analytics_service import analytics_service

# Инициализация бота и диспетчера с хранилищем состояний
bot = Bot(token=config.bot_token)
dp = Dispatcher(storage=MemoryStorage())

# Регистрация обработчиков
test_handler = TestHandler()
full_version_handler = FullVersionHandler()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Обработчик команды /start
    Отправляет приветственное сообщение и кнопки для начала теста и полной версии
    """
    user_id = message.from_user.id
    logger.info(f"Received /start command from user {user_id}")
    
    # Записываем активацию бота в аналитику
    analytics_service.log_activation(user_id)

    # Создаем клавиатуру с кнопками
    keyboard = []
    
    # Кнопка начала демо-теста
    keyboard.append([InlineKeyboardButton(text="🎯 Начать демо-тест", callback_data="start_test")])
    
    # Кнопка полной версии
    keyboard.append([InlineKeyboardButton(text="✨ Полная версия 149 руб/мес", callback_data="full_version")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Удаляем предыдущее сообщение, если было
    await message_manager.delete_last_message(user_id)
    
    # Отправляем новое приветственное сообщение с HTML-форматированием
    new_message = await message.answer(
        config.messages["welcome"], 
        reply_markup=reply_markup, 
        parse_mode="HTML"
    )
    
    # Сохраняем сообщение как последнее
    message_manager.last_messages[user_id] = new_message
    
    logger.info("Sent welcome message with buttons")


@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    """
    Обработчик команды /cancel
    Отменяет текущий тест
    """
    user_id = message.from_user.id
    logger.info(f"Received /cancel command from user {user_id}")
    test_handler.test_service.end_test(user_id)
    
    # Удаляем предыдущее сообщение
    await message_manager.delete_last_message(user_id)
    
    # Отправляем новое сообщение
    new_message = await message.answer("Тест отменен. Отправьте /start чтобы начать новый тест.")
    
    # Сохраняем как последнее сообщение
    message_manager.last_messages[user_id] = new_message


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """
    Обработчик команды /stats
    Отправляет статистику использования бота.
    Доступно только для администратора.
    """
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id != config.admin_id:
        logger.info(f"User {user_id} tried to access stats but is not an admin")
        await message.answer("У вас нет доступа к этой команде.")
        return
    
    logger.info(f"Admin {user_id} requested stats")
    
    # Получаем статистику
    stats = analytics_service.get_statistics()
    stats_text = analytics_service.format_statistics(stats)
    
    # Удаляем предыдущее сообщение
    await message_manager.delete_last_message(user_id)
    
    # Отправляем новое сообщение со статистикой
    new_message = await message.answer(
        stats_text,
        parse_mode="HTML"
    )
    
    # Сохраняем как последнее сообщение
    message_manager.last_messages[user_id] = new_message


@dp.message(Command("echo"))
async def cmd_echo(message: types.Message):
    """
    Отладочный обработчик
    Отвечает на сообщение пользователя тем же текстом
    """
    user_id = message.from_user.id
    logger.info(f"Echo command from user {user_id}: {message.text}")
    
    # Удаляем предыдущее сообщение
    await message_manager.delete_last_message(user_id)
    
    # Отправляем новое сообщение
    new_message = await message.answer(f"Вы написали: {message.text}")
    
    # Сохраняем как последнее сообщение
    message_manager.last_messages[user_id] = new_message


@dp.message(F.text)
async def handle_text(message: types.Message):
    """
    Отладочный обработчик для всех текстовых сообщений
    """
    user_id = message.from_user.id
    logger.info(f"Received text message from user {user_id}: {message.text}")
    
    # Удаляем предыдущее сообщение
    await message_manager.delete_last_message(user_id)
    
    # Отправляем новое сообщение
    new_message = await message.answer("Используйте /start для начала теста или /cancel для отмены текущего теста.")
    
    # Сохраняем как последнее сообщение
    message_manager.last_messages[user_id] = new_message


@dp.callback_query(lambda c: c.data == 'start_test')
async def start_test(callback_query: types.CallbackQuery):
    """
    Обработчик нажатия кнопки "Начать демо-тест"
    Запускает тестирование для пользователя
    """
    logger.info(
        f"User {callback_query.from_user.id} clicked start_test button")
    await callback_query.answer()
    try:
        await test_handler.handle_start_test(callback_query)
    except Exception as e:
        logger.error(f"Error starting test: {str(e)}")
        user_id = callback_query.from_user.id
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение об ошибке
        error_message = await callback_query.message.answer(
            "Произошла ошибка при запуске теста. Попробуйте еще раз позже.")
            
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = error_message


@dp.callback_query(lambda c: c.data.startswith('answer_'))
async def handle_answer(callback_query: types.CallbackQuery, state: FSMContext = None):
    """
    Обработчик ответов на вопросы теста
    """
    logger.info(
        f"User {callback_query.from_user.id} answered with {callback_query.data}"
    )
    await callback_query.answer()
    try:
        # Проверяем текущее состояние
        current_state = None
        if state:
            current_state = await state.get_state()
            
        from handlers.full_version_handler import FullVersionStates
        
        # Если пользователь в состоянии полной версии
        if current_state == FullVersionStates.ANSWERING:
            await full_version_handler.handle_answer(callback_query, state)
        else:
            # Стандартная версия
            await test_handler.handle_answer(callback_query)
    except Exception as e:
        logger.error(f"Error handling answer: {str(e)}")
        user_id = callback_query.from_user.id
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение об ошибке
        error_message = await callback_query.message.answer(
            "Произошла ошибка. Пожалуйста, начните тест заново с помощью команды /start")
            
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = error_message


@dp.callback_query(lambda c: c.data.startswith('checklist_'))
async def handle_checklist_button(callback_query: types.CallbackQuery):
    """
    Обработчик кнопки получения чек-листа
    """
    logger.info(
        f"User {callback_query.from_user.id} requested checklist with {callback_query.data}"
    )
    await callback_query.answer()
    try:
        await test_handler.handle_checklist(callback_query)
    except Exception as e:
        logger.error(f"Error handling checklist request: {str(e)}")
        user_id = callback_query.from_user.id
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение об ошибке
        error_message = await callback_query.message.answer(
            "Произошла ошибка при формировании чек-листа. Пожалуйста, попробуйте позже.")
            
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = error_message


@dp.callback_query(lambda c: c.data == 'full_version')
async def handle_full_version_button(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки полной версии
    """
    user = callback_query.from_user
    user_id = user.id
    logger.info(
        f"User {user_id} ({user.username or 'без username'}) requested full version"
    )
    
    # Проверяем, авторизован ли пользователь
    is_authorized = config.is_user_authorized(user_id)
    
    # Если пользователь не авторизован, отправляем уведомление администратору
    if not is_authorized and config.admin_id:
        # Уведомление о запросе доступа для администратора
        admin_notification = f"""
<b>⚠️ Запрос на доступ к полной версии</b>

<b>Пользователь:</b>
ID: {user_id}
Имя: {user.full_name}
Username: @{user.username or 'отсутствует'}

<b>Время запроса:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

Чтобы добавить пользователя, обновите список config.authorized_users.
"""
        try:
            await bot.send_message(config.admin_id, admin_notification, parse_mode="HTML")
            logger.info(f"Notification about access request sent to admin (ID: {config.admin_id})")
            
            # Отправляем подтверждение пользователю
            await callback_query.answer("Ваш запрос на доступ отправлен администратору")
            
        except Exception as admin_error:
            logger.error(f"Failed to send notification to admin: {str(admin_error)}")
            # Если не удалось отправить уведомление админу, все равно даем знать пользователю
            await callback_query.answer("Запрос обрабатывается")
    
    try:
        await full_version_handler.handle_full_version_start(callback_query, state)
    except Exception as e:
        logger.error(f"Error handling full version request: {str(e)}")
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение об ошибке
        error_message = await callback_query.message.answer(
            "Произошла ошибка. Пожалуйста, попробуйте позже.")
            
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = error_message


@dp.callback_query(lambda c: c.data.startswith('topic_'))
async def handle_topic_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обработчик выбора темы в полной версии
    """
    logger.info(f"User {callback_query.from_user.id} selected topic {callback_query.data}")
    try:
        await full_version_handler.handle_topic_selection(callback_query, state)
    except Exception as e:
        logger.error(f"Error handling topic selection: {str(e)}")
        user_id = callback_query.from_user.id
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение об ошибке
        error_message = await callback_query.message.answer(
            "Произошла ошибка при выборе темы. Пожалуйста, попробуйте позже.")
            
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = error_message


@dp.callback_query(lambda c: c.data == 'full_checklist')
async def handle_full_checklist_button(callback_query: types.CallbackQuery):
    """
    Обработчик кнопки получения персонализированного чек-листа в полной версии
    """
    logger.info(f"User {callback_query.from_user.id} requested full checklist")
    try:
        await full_version_handler.handle_checklist_request(callback_query)
    except Exception as e:
        logger.error(f"Error handling full checklist request: {str(e)}")
        user_id = callback_query.from_user.id
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение об ошибке
        error_message = await callback_query.message.answer(
            "Произошла ошибка при формировании чек-листа. Пожалуйста, попробуйте позже.")
            
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = error_message


@dp.callback_query(lambda c: c.data == 'continue_test')
async def handle_continue_test_button(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки продолжения теста с новыми вопросами в полной версии
    """
    logger.info(f"User {callback_query.from_user.id} requested to continue test with new questions")
    try:
        await full_version_handler.handle_continue_test(callback_query, state)
    except Exception as e:
        logger.error(f"Error handling continue test: {str(e)}")
        user_id = callback_query.from_user.id
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение об ошибке
        error_message = await callback_query.message.answer(
            "Произошла ошибка при генерации новых вопросов. Пожалуйста, попробуйте позже.")
            
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = error_message


@dp.callback_query(lambda c: c.data == 'continue_demo_test')
async def handle_continue_demo_test_button(callback_query: types.CallbackQuery):
    """
    Обработчик кнопки продолжения теста с новыми вопросами в демо-версии
    """
    logger.info(f"User {callback_query.from_user.id} requested to continue demo test with new questions")
    try:
        await test_handler.handle_continue_demo_test(callback_query)
    except Exception as e:
        logger.error(f"Error handling continue demo test: {str(e)}")
        user_id = callback_query.from_user.id
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение об ошибке
        error_message = await callback_query.message.answer(
            "Произошла ошибка при генерации новых вопросов. Пожалуйста, попробуйте позже.")
            
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = error_message


@dp.callback_query(lambda c: c.data == 'back_to_main')
async def handle_back_to_main_button(callback_query: types.CallbackQuery):
    """
    Обработчик кнопки возврата в главное меню
    """
    logger.info(f"User {callback_query.from_user.id} requested to go back to main menu")
    try:
        await full_version_handler.handle_back_to_main(callback_query)
    except Exception as e:
        logger.error(f"Error handling back to main: {str(e)}")
        user_id = callback_query.from_user.id
        
        # Удаляем предыдущее сообщение
        await message_manager.delete_last_message(user_id)
        
        # Отправляем сообщение об ошибке
        error_message = await callback_query.message.answer(
            "Произошла ошибка. Пожалуйста, используйте команду /start для возврата в главное меню.")
            
        # Сохраняем как последнее сообщение
        message_manager.last_messages[user_id] = error_message


async def main():
    logger.info("Starting bot...")
    try:
        # Проверяем наличие токена
        if not config.bot_token:
            logger.error("Bot token is not set!")
            return
            
        # Устанавливаем команды в меню бота
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Меню")
        ])

        logger.info("Bot initialization completed successfully")
        logger.info("Starting polling...")

        # Запускаем бота
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Critical error while running bot: {str(e)}",
                     exc_info=True)
        raise


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {str(e)}")
