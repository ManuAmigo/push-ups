# utils/logger.py
import inspect
import logging
import pathlib
import textwrap
from pathlib import Path

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# --- 🧠 Хранилище разрешённых модулей ---
_allowed_named_loggers = set()


class NamedFilter(logging.Filter):
    """Пропускает только разрешённые модули"""
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
        header = " | ".join(parts[:3])
        message = parts[3]
        wrapped = textwrap.fill(message, width=self.width, subsequent_indent=self.indent)
        return f"{header} | {wrapped}"


def get_named_logger(level=logging.DEBUG) -> logging.Logger:
    """
    Возвращает логгер с именем текущего модуля, и добавляет его в список разрешённых.
    """
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    filename = pathlib.Path(module.__file__).stem if module and module.__file__ else "__main__"

    _allowed_named_loggers.add(filename)  # 💥 Регистрируем модуль как разрешённый
    logger = logging.getLogger(filename)
    logger.setLevel(level)
    return logger


def setup_logger(mode: str = "named", log_file: str = "bot.log", level=logging.INFO) -> None:
    log_path = LOGS_DIR / log_file

    file_formatter = WrappedFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%m-%d %H:%M:%S",
        width=100,
        indent=" " * 42
    )

    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    if mode == "silent":
        logging.getLogger().handlers.clear()
        logging.getLogger().disabled = True
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    if mode == "all":
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    elif mode == "named":
        file_handler.addFilter(NamedFilter())
        console_handler.addFilter(NamedFilter())
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    else:
        raise ValueError("Неверный режим логгирования. Используй 'all', 'named' или 'silent'")
