# Добавляем поток вывода в файл
import logging
from logging.handlers import RotatingFileHandler

from programm_files import log_dir, init_dirs

init_dirs()

fp = fr'{log_dir}\log.log'

file_log = logging.FileHandler(fp)
my_handler = RotatingFileHandler(fp, mode='a', maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
my_handler.setLevel(logging.DEBUG)

# И вывод в консоль
console_out = logging.StreamHandler()

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s', handlers=(file_log, console_out))