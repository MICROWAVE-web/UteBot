# Добавляем поток вывода в файл
import logging
from programm_files import log_dir

file_log = logging.FileHandler(fr'{log_dir}\log.log')

# И вывод в консоль
console_out = logging.StreamHandler()

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s', handlers=(file_log, console_out))