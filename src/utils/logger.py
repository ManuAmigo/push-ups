# utils/logger.py
import inspect
import logging
import pathlib
from pathlib import Path

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


class NamedFilter(logging.Filter):
    """Пропускает только логи из bot.py и main.py (по имени логгера)"""
    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith("bot") or record.name.startswith("main")


def get_named_logger(level=logging.DEBUG) -> logging.Logger:
    """
    Возвращает логгер с именем текущего файла (без .py).
    Например: main.py → logger с именем 'main'
    """
    # Получаем имя вызывающего файла
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    filename = pathlib.Path(module.__file__).stem if module and module.__file__ else "__main__"

    logger = logging.getLogger(filename)
    logger.setLevel(level)
    return logger

def setup_logger(mode: str = "named", log_file: str = "bot.log", level=logging.INFO) -> None:
    """
    Настраивает логирование.

    :param mode:
        - "all" — логировать всё (root logger)
        - "named" — только bot.py и main.py
        - "silent" — отключить логирование полностью
    """
    log_path = LOGS_DIR / log_file

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    if mode == "silent":
        logging.getLogger().handlers.clear()
        logging.getLogger().disabled = True
        return

    if mode == "all":
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers.clear()
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        logging.getLogger().disabled = False

    elif mode == "named":
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers.clear()
        file_handler.addFilter(NamedFilter())
        console_handler.addFilter(NamedFilter())
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        logging.getLogger().disabled = False

    else:
        raise ValueError("Неверный режим логгирования. Используй 'all', 'named' или 'silent'")
