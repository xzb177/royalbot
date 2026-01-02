"""
魔法工坊 - 配置文件
从 .env 加载敏感信息
"""
import os
from pathlib import Path

def _load_dotenv(dotenv_path: Path) -> None:
    """简易 .env 加载器"""
    if not dotenv_path.exists():
        return
    for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        os.environ.setdefault(k, v)

# 加载 .env
_load_dotenv(Path(__file__).parent / ".env")

class Config:
    # Telegram
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    OWNER_ID = int(os.getenv("OWNER_ID", 5779291957))
    GROUP_ID = int(os.getenv("GROUP_ID", -1002306960410))

    # 消息自毁配置（秒），设为 0 则不删除
    MESSAGE_DELETE_DELAY = int(os.getenv("MESSAGE_DELETE_DELAY", 30))

    # Emby
    EMBY_URL = os.getenv("EMBY_URL", "")
    EMBY_API_KEY = os.getenv("EMBY_API_KEY", "")
    EMBY_LIBRARY_WHITELIST = os.getenv("EMBY_LIBRARY_WHITELIST", "")

    # Database
    DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # sqlite / postgresql / mysql
    DB_PATH = os.getenv("DB_PATH", "data/magic.db")
    DB_URL = os.getenv("DB_URL", f"sqlite:///{DB_PATH}")
    DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"  # SQL日志开关

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise RuntimeError("BOT_TOKEN 未设置！请检查 .env 文件")
