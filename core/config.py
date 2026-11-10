import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    BASE_DIR: Path = BASE_DIR
    TEMP_DIR: Path = BASE_DIR / "temp"
    OUTPUT_DIR: Path = BASE_DIR / "output"

    # Telegram Bot Token (support various casings)
    TELEGRAM_BOT_TOKEN: str = (
        os.getenv("TELEGRAM_BOT_TOKEN")
        or os.getenv("Telegram_BOT_TOKEN")
        or os.getenv("BOT_TOKEN")
        or ""
    ).strip()

    # Gemini Multi-Keys
    @classmethod
    def get_gemini_keys(cls) -> List[str]:
        keys = []
        # Check GEMINI_KEY_1, GEMINI_KEY_2, GEMINI_API_KEYS1, GEMINI_API_KEY_1...
        for i in range(1, 10):
            candidates = [
                f"GEMINI_KEY_{i}",
                f"GEMINI_API_KEYS{i}",
                f"GEMINI_API_KEY_{i}",
                f"GEMINI_KEY{i}",
                f"GEMINI_API_KEYS_{i}"
            ]
            for var_name in candidates:
                k = os.getenv(var_name, "").strip()
                if k and k not in keys:
                    keys.append(k)
        
        # Check comma-separated GEMINI_API_KEYS
        bulk_keys = os.getenv("GEMINI_API_KEYS", "").strip()
        if bulk_keys:
            for k in bulk_keys.split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)

        # Single key fallback
        single_key = os.getenv("GEMINI_API_KEY", "").strip()
        if single_key and single_key not in keys:
            keys.append(single_key)

        return keys

    # Clipper parameters
    MAX_HIGHLIGHTS: int = int(os.getenv("MAX_HIGHLIGHTS", "3"))
    MIN_CLIP_DURATION: int = int(os.getenv("MIN_CLIP_DURATION", "30"))
    MAX_CLIP_DURATION: int = int(os.getenv("MAX_CLIP_DURATION", "90"))
    PREFERRED_RESOLUTION: int = int(os.getenv("PREFERRED_RESOLUTION", "720"))

    # Anti-bot cookies resolution (Portable between Windows and Linux VPS)
    @classmethod
    def get_cookies_path(cls) -> str:
        cookies_env = os.getenv("COOKIES_PATH", "").strip()
        if cookies_env:
            p = Path(cookies_env)
            if not p.is_absolute():
                p = cls.BASE_DIR / p
            if p.exists():
                return str(p)
            # If user had a Windows path on Linux, try basename in BASE_DIR
            basename_p = cls.BASE_DIR / p.name
            if basename_p.exists():
                return str(basename_p)

        # Auto-detect cookies.txt in BASE_DIR if present
        default_cookies = cls.BASE_DIR / "cookies.txt"
        if default_cookies.exists():
            return str(default_cookies)

        return ""

    # Whitelisted Telegram User IDs
    @classmethod
    def get_allowed_user_ids(cls) -> List[int]:
        raw = (os.getenv("ALLOWED_USER_ID") or os.getenv("ALLOWED_USER_IDS") or "").strip()
        if not raw:
            return []
        ids = []
        for part in raw.replace(";", ",").split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError:
                pass
        return ids

    @classmethod
    def is_user_allowed(cls, user_id: int) -> bool:
        allowed = cls.get_allowed_user_ids()
        if not allowed:
            # If no ID is configured, restrict all access by default for security
            return False
        return user_id in allowed

    # Gemini Model preference (Default to active lightning-fast gemini-3.5-flash-lite)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    @classmethod
    def ensure_directories(cls):
        try:
            cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
            cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass


# Initialize folders
Config.ensure_directories()
