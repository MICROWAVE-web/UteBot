# Добавляем поток вывода в файл
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

from pytz import timezone

from programm_files import log_dir, init_dirs

init_dirs()

fp = fr'{log_dir}\log.log'

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
