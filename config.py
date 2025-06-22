import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
BOT_TOKEN = "7728088084:AAHHm-uhMuSg1IWc4eiS8OAhZiF3eUEDA4E"
CHAT_ID = -1001755175377

# Event Configuration
MAX_PARTICIPANTS = 18
SCHEDULE_HOUR = 21
SCHEDULE_MINUTE = 0
SCHEDULE_DAY = 6  # Sunday (0=Monday, 6=Sunday)

# Message Configuration
PIN_MESSAGE = True  # Закреплять ли сообщение со списком
PIN_NOTIFICATION = False  # Показывать ли уведомление о закреплении

# Database Configuration
DATABASE_PATH = "participants.db"  