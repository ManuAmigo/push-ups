import inspect
import logging
import pathlib
import textwrap
import re
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path

from colorlog import ColoredFormatter


# 🧭 Путь к logs рядом с файлом
LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


# --- 🧠 Разрешённые модули ---
_allowed_named_loggers = set()


class LogMode(Enum):
    ALL = "all"
    NAMED = "named"
    SILENT = "silent"


class NamedFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.name in _allowed_named_loggers


class WrappedFormatter(logging.Formatter):
    def __init__(self, *args, width: int = 100, indent: str = " " * 42, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = width
        self.indent = indent

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        parts = original.split(" | ", 3)
        if len(parts) < 4:
            return original
        header = " ".join(parts[:3])
        message = parts[3]
        wrapped = textwrap.fill(message, width=self.width, subsequent_indent=self.indent)
        return f"{header} | {wrapped}"


def get_named_logger(level=logging.DEBUG) -> logging.Logger:
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    filename = pathlib.Path(module.__file__).stem if module and module.__file__ else "__main__"

    _allowed_named_loggers.add(filename)
    logger = logging.getLogger(filename)
    logger.setLevel(level)
    return logger


def cleanup_old_logs(days: int = 8):
    cutoff_date = datetime.now() - timedelta(days=days)
    for log_file in LOGS_DIR.glob("bot_*.log"):
        match = re.search(r"bot_(\d{4}-\d{2}-\d{2})\.log", log_file.name)
        if match:
            try:
                file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                if file_date < cutoff_date:
                    log_file.unlink()
                    logging.getLogger("logger").info(f"🧹 Старый лог удалён: {log_file.name}")
            except Exception as e:
                logging.getLogger("logger").warning(f"⚠️ Не удалось удалить {log_file.name}: {e}")


def setup_logger(mode: LogMode = LogMode.NAMED, log_file: str = None, level=logging.INFO) -> None:
    today_str = datetime.now().strftime("%Y-%m-%d")
    log_filename = log_file or f"bot_{today_str}.log"
    log_path = LOGS_DIR / log_filename

    cleanup_old_logs(days=30)

    file_formatter = WrappedFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%m-%d %H:%M:%S"
    )

    console_formatter = ColoredFormatter(
        fmt="%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    if mode == LogMode.SILENT:
        root_logger.disabled = True
        return

    if mode == LogMode.ALL:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    elif mode == LogMode.NAMED:
        file_handler.addFilter(NamedFilter())
        console_handler.addFilter(NamedFilter())
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    else:
        raise ValueError(f"❌ Неверный режим логгирования: {mode}")
