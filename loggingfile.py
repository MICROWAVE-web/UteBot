# Добавляем поток вывода в файл
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from pytz import timezone

from programm_files import init_dirs, data_dir, logs_folder

init_dirs()

fp = fr'{logs_folder}\log.txt'

# file_log = logging.FileHandler(fp)
my_handler = RotatingFileHandler(fp, mode='a', maxBytes=10 * 1024 * 1024, backupCount=10, encoding='utf-8')
my_handler.setLevel(logging.DEBUG)

# И вывод в консоль
console_out = logging.StreamHandler()


def timetz(*args):
    return datetime.now(timezone('Etc/GMT-3')).timetuple()


logging.Formatter.converter = timetz

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s', handlers=(my_handler, console_out))


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    # Пропускаем KeyboardInterrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Логируем или выводим в консоль
    logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    # Или:
    # traceback.print_exception(exc_type, exc_value, exc_traceback)


# Назначаем глобальный перехват
sys.excepthook = log_unhandled_exception
