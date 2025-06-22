import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import config
from database import DatabaseManager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
db_manager = DatabaseManager()
scheduler = AsyncIOScheduler()

def get_next_sunday_date() -> str:
    """Получение даты ближайшего воскресенья"""
    today = datetime.now()
    days_ahead = config.SCHEDULE_DAY - today.weekday()
    if days_ahead <= 0:  # Если сегодня воскресенье или прошло
        days_ahead += 7
    next_sunday = today + timedelta(days=days_ahead)
    return next_sunday.strftime('%Y-%m-%d')

def format_participants_list(participants: list, event_date: str) -> str:
    """Форматирование списка участников"""
    header = f"📅 Список участников на {event_date}\n"
    header += f"👥 Мест: {len(participants)}/{config.MAX_PARTICIPANTS}\n\n"
    
    if not participants:
        return header + "Список пуст. Нажмите 'Участвовать' чтобы записаться!"
    
    participants_text = ""
    for i, (user_id, username, first_name, last_name, position) in enumerate(participants, 1):
        name = f"{first_name or ''} {last_name or ''}".strip()
        if username:
            name = f"@{username}" if not name else f"{name} (@{username})"
        elif not name:
            name = f"User {user_id}"
        
        participants_text += f"{position}. {name}\n"
    
    return header + participants_text

def get_participation_keyboard(event_date: str) -> InlineKeyboardMarkup:
    """Создание клавиатуры для участия"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Участвовать", 
                callback_data=f"join:{event_date}"
            ),
            InlineKeyboardButton(
                text="❌ Отказаться", 
                callback_data=f"leave:{event_date}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Обновить список", 
                callback_data=f"refresh:{event_date}"
            )
        ]
    ])

async def send_weekly_list():
    """Отправка еженедельного списка"""
    try:
        event_date = get_next_sunday_date()
        
        # Форматируем текст сообщения
        text = format_participants_list([], event_date)
        keyboard = get_participation_keyboard(event_date)
        
        # Отправляем сообщение
        message = await bot.send_message(
            chat_id=config.CHAT_ID,
            text=text,
            reply_markup=keyboard
        )
        
        # Закрепляем сообщение, если включена эта опция
        if config.PIN_MESSAGE:
            try:
                await bot.pin_chat_message(
                    chat_id=config.CHAT_ID,
                    message_id=message.message_id,
                    disable_notification=not config.PIN_NOTIFICATION
                )
                logger.info(f"Message pinned for {event_date}")
            except Exception as pin_error:
                logger.warning(f"Failed to pin message: {pin_error}")
                logger.warning("Bot might not have admin rights to pin messages")
        
        # Сохраняем событие в базе данных
        await db_manager.create_event(event_date, message.message_id)
        
        logger.info(f"Weekly list sent for {event_date}")
        
    except Exception as e:
        logger.error(f"Error sending weekly list: {e}")

@dp.callback_query(F.data.startswith("join:"))
async def handle_join(callback: CallbackQuery):
    """Обработка записи на участие"""
    try:
        # Отвечаем на callback быстро для предотвращения таймаута
        await callback.answer("Обрабатываем запрос...")
        
        if not callback.data or not callback.message:
            await callback.answer("Ошибка данных", show_alert=True)
            return
            
        event_date = callback.data.split(":")[1]
        user = callback.from_user
        
        # Получаем событие из базы данных
        event = await db_manager.get_event_by_date(event_date)
        if not event:
            await callback.answer("Событие не найдено", show_alert=True)
            return
        
        event_id = event[0]
        
        # Добавляем участника
        success, position = await db_manager.add_participant(
            event_id=event_id,
            user_id=user.id,
            username=user.username or "",
            first_name=user.first_name or "",
            last_name=user.last_name or ""
        )
        
        if success:
            # Получаем обновленный список участников
            participants = await db_manager.get_participants(event_id)
            
            # Обновляем сообщение
            text = format_participants_list(participants, event_date)
            keyboard = get_participation_keyboard(event_date)
            
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard
            )
            
            await callback.answer(f"Вы записаны под номером {position}!")
            
        elif position == -1:
            await callback.answer("Список полон!", show_alert=True)
        else:
            await callback.answer(f"Вы уже записаны под номером {position}")
            
    except Exception as e:
        logger.error(f"Error in handle_join: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@dp.callback_query(F.data.startswith("leave:"))
async def handle_leave(callback: CallbackQuery):
    """Обработка отказа от участия"""
    try:
        await callback.answer("Обрабатываем запрос...")
        
        if not callback.data or not callback.message:
            await callback.answer("Ошибка данных", show_alert=True)
            return
            
        event_date = callback.data.split(":")[1]
        user = callback.from_user
        
        # Получаем событие из базы данных
        event = await db_manager.get_event_by_date(event_date)
        if not event:
            await callback.answer("Событие не найдено", show_alert=True)
            return
        
        event_id = event[0]
        
        # Удаляем участника
        success = await db_manager.remove_participant(event_id, user.id)
        
        if success:
            # Получаем обновленный список участников
            participants = await db_manager.get_participants(event_id)
            
            # Обновляем сообщение
            text = format_participants_list(participants, event_date)
            keyboard = get_participation_keyboard(event_date)
            
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard
            )
            
            await callback.answer("Вы удалены из списка!")
        else:
            await callback.answer("Вас нет в списке")
            
    except Exception as e:
        logger.error(f"Error in handle_leave: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@dp.callback_query(F.data.startswith("refresh:"))
async def handle_refresh(callback: CallbackQuery):
    """Обработка обновления списка"""
    try:
        await callback.answer("Обновляем список...")
        
        if not callback.data or not callback.message:
            await callback.answer("Ошибка данных", show_alert=True)
            return
            
        event_date = callback.data.split(":")[1]
        
        # Получаем событие из базы данных
        event = await db_manager.get_event_by_date(event_date)
        if not event:
            await callback.answer("Событие не найдено", show_alert=True)
            return
        
        event_id = event[0]
        
        # Получаем список участников
        participants = await db_manager.get_participants(event_id)
        
        # Обновляем сообщение
        text = format_participants_list(participants, event_date)
        keyboard = get_participation_keyboard(event_date)
        
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in handle_refresh: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда старт"""
    await message.answer("Бот запущен! Еженедельные списки будут отправляться каждое воскресенье в 21:00")

@dp.message(Command("test"))
async def cmd_test(message: types.Message):
    """Тестовая команда для отправки списка"""
    if message.chat.id == config.CHAT_ID:
        await send_weekly_list()
        await message.answer("✅ Тестовый список отправлен!")
    else:
        await message.answer(
            f"❌ Команда работает только в настроенном чате!\n"
            f"Текущий чат: {message.chat.id}\n"
            f"Настроенный чат: {config.CHAT_ID}\n\n"
            f"Для тестирования используйте бота в чате {config.CHAT_ID}"
        )

async def main():
    """Главная функция"""
    # Инициализация базы данных
    await db_manager.init_database()
    
    # Настройка планировщика
    scheduler.add_job(
        send_weekly_list,
        trigger=CronTrigger(
            day_of_week=config.SCHEDULE_DAY,
            hour=config.SCHEDULE_HOUR,
            minute=config.SCHEDULE_MINUTE
        ),
        id="weekly_list",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started")
    
    # Запуск бота
    logger.info("Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 