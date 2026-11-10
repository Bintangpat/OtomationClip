import logging
from aiogram import Bot, Dispatcher
from core.config import Config
from core.queue_manager import QueueManager
from bot.handlers import router, set_queue_manager
from bot.middlewares import AuthMiddleware

logger = logging.getLogger(__name__)


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher, QueueManager]:
    token = Config.TELEGRAM_BOT_TOKEN
    if not token or token == "123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ":
        logger.warning("TELEGRAM_BOT_TOKEN is not configured in .env file.")

    bot = Bot(token=token or "dummy:token")
    dp = Dispatcher()

    # Register Security Middleware to protect all incoming messages
    dp.message.middleware(AuthMiddleware())

    queue_manager = QueueManager(bot=bot)
    set_queue_manager(queue_manager)

    dp.include_router(router)

    return bot, dp, queue_manager
