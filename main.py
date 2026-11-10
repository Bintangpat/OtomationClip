import asyncio
import logging
import sys
from core.config import Config
from bot.telegram_app import create_bot_and_dispatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AutoClipperMain")


async def main():
    logger.info("==================================================")
    logger.info("   AUTO-CLIPPER YOUTUBE & SMART SUMMARIZER BOT   ")
    logger.info("==================================================")

    # 1. Ensure storage directories
    Config.ensure_directories()
    logger.info(f"Base Directory: {Config.BASE_DIR}")
    logger.info(f"Temp Directory: {Config.TEMP_DIR}")
    logger.info(f"Output Directory: {Config.OUTPUT_DIR}")

    # 2. Check Gemini Keys
    keys = Config.get_gemini_keys()
    logger.info(f"Loaded {len(keys)} Gemini API Key(s) for multi-key rotation.")
    if not keys:
        logger.warning("No Gemini API keys found! Please set GEMINI_KEY_1 in .env")

    # 3. Check Telegram Token
    if not Config.TELEGRAM_BOT_TOKEN or "ABCDefGh" in Config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured! Please set it in .env")

    # 4. Security Whitelist Check
    allowed_ids = Config.get_allowed_user_ids()
    if allowed_ids:
        logger.info(f"Security: Whitelist enabled for {len(allowed_ids)} Telegram user ID(s): {allowed_ids}")
    else:
        logger.warning("Security: ALLOWED_USER_ID is empty! All messages will be blocked until ALLOWED_USER_ID is configured in .env.")

    # 5. Initialize Bot & Dispatcher
    bot, dp, queue_manager = create_bot_and_dispatcher()

    # 6. Start Background Queue Worker
    queue_manager.start()

    try:
        logger.info("Starting Telegram Bot polling loop...")
        await dp.start_polling(bot, allowed_updates=["message"])
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down bot...")
    finally:
        await queue_manager.stop()
        await bot.session.close()
        logger.info("Bot and queue successfully stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application exited cleanly.")
