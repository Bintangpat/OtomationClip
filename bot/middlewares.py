import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from core.config import Config

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Middleware to restrict access only to users specified in ALLOWED_USER_ID (.env).
    Blocks unauthorized users and informs them of their Telegram User ID.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        from_user = getattr(event, "from_user", None)
        if from_user:
            user_id = from_user.id
            if not Config.is_user_allowed(user_id):
                user_info = f"@{from_user.username}" if from_user.username else from_user.full_name
                logger.warning(f"Unauthorized message blocked from {user_info} (ID: {user_id})")
                
                answer_func = getattr(event, "answer", None)
                if callable(answer_func):
                    await answer_func(
                        f"⛔ *Akses Ditolak*\n\n"
                        f"Bot ini bersifat privat dan hanya merespons pengguna yang diizinkan.\n\n"
                        f"🆔 *User ID Anda:* `{user_id}`\n\n"
                        f"💡 *Cara Mengaktifkan:*\n"
                        f"Tambahkan ID Anda ke variabel `ALLOWED_USER_ID` pada file `.env`:\n"
                        f"`ALLOWED_USER_ID={user_id}`\n"
                        f"Kemudian simpan dan jalankan kembali bot.",
                        parse_mode="Markdown"
                    )
                return

        return await handler(event, data)
