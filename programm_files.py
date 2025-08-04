import json
import logging
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from filelock import FileLock
from platformdirs import *

CURRENT_VERSION = '1.0.4.2'  # Текущая версия бота

appname = f"UTEConnect_{CURRENT_VERSION}"

appauthor = "UTEConnect"

# Получаем путь к текущему исполняемому файлу (если .exe, то он будет корректным)
EXE_PATH = Path(sys.argv[0]).resolve()
print(EXE_PATH)

# Определяем путь к файлу привязки в конфигурационной директории пользователя
CONFIG_DIR = Path(user_data_dir(appname, appauthor))
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "instances.json"


def load_instances():
    """Загружает привязки экземпляров из файла."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass  # Если файл повреждён, игнорируем его

    return {}


def save_instances(instances):
    """Сохраняет обновлённые привязки экземпляров."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(instances, f, indent=4)


def get_or_create_instance_directory():
    """Определяет уникальную папку для данного экземпляра программы."""
    instances = load_instances()
    exe_key = str(EXE_PATH)  # Уникальный ключ для текущего .exe

    if exe_key in instances:
        instance_dir = Path(instances[exe_key])
        if instance_dir.exists():
            return instance_dir  # Возвращаем привязанную папку

    # Если привязки нет, создаём новую папку
    new_instance_dir = CONFIG_DIR / f"instance_{uuid.uuid4().hex}"
    new_instance_dir.mkdir(parents=True, exist_ok=True)

    # Сохраняем привязку
    instances[exe_key] = str(new_instance_dir)
    save_instances(instances)

    return new_instance_dir


def init_dirs():
    print(data_dir, log_dir)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(logs_folder, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)


def save_money_management_data(mm_data):
    with open(fr'{data_dir}\mm_data.log', 'w', encoding='utf-8') as f:
        json.dump(mm_data, f, indent=4, ensure_ascii=False)


def load_money_management_data():
    try:
        with open(fr'{data_dir}\mm_data.log', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def validate_statistic_data(data):
    return isinstance(data, dict) and "summary" in data and "trades" in data


def save_statistic_data(statistic_data):
    if not validate_statistic_data(statistic_data):
        print("❌ Некорректная структура данных. Сохранение отменено.")
        return

    path = os.path.join(data_dir, 'statistic_data.json')
    lock_path = path + '.lock'
    backup_path = path + '.bak'

    with FileLock(lock_path):
        # Создаём резервную копию, если файл уже есть
        if os.path.exists(path):
            shutil.copy2(path, backup_path)

        # Сохраняем данные во временный файл
        temp_fd, temp_path = tempfile.mkstemp(dir=data_dir, suffix='.tmp')
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as tmp_file:
                json.dump(statistic_data, tmp_file, indent=4, ensure_ascii=False)

            # Атомарная замена основного файла
            shutil.move(temp_path, path)

        except Exception as e:
            print(f"❌ Ошибка при сохранении: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            # Восстанавливаем из резервной копии
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, path)


def load_statistic_data():
    try:
        with open(fr'{data_dir}\statistic_data.json', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "summary": {
            },
            "trades": [],
        }


def save_auth_data(auth_data):
    with open(fr'{data_dir}\auth_data.log', 'w', encoding='utf-8') as f:
        json.dump(auth_data, f, indent=4, ensure_ascii=False)


def load_auth_data():
    try:
        with open(fr'{data_dir}\auth_data.log', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_additional_settings_data(auth_data):
    try:
        with open(fr'{data_dir}\additional_settings_data.json', 'w', encoding='utf-8') as f:
            json.dump(auth_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error saving settings: {str(e)}")


"""
{
    "pairs": {
        "EURUSD": True,
        "GBPUSD": False,
        # ...
    },
    "schedule": {
        "Пн": {"enabled": True, "start": "09:00", "end": "23:59"},
        "Вт": {"enabled": True, "start": "09:00", "end": "17:00"},
        "Ср": {"enabled": False, "start": "00:00", "end": "00:00"},
        # ...
    }
}
"""


def load_additional_settings_data(reset=False):
    try:
        if os.path.exists(fr'{data_dir}\\additional_settings_data.json') and not reset:
            with open(fr'{data_dir}\\additional_settings_data.json', "r", encoding="utf-8") as f:
                result = json.load(f)
                if "Пн" in result.get("schedule", {}).keys():
                    load_additional_settings_data(reset=True)
                return result
        else:
            # Создаем настройки по умолчанию
            default_settings = {
                "pairs": {},
                "schedule": {
                    "0": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "1": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "2": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "3": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "4": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "5": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "6": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                },
                "theme": "dark"
            }
            save_additional_settings_data(default_settings)
            return default_settings
    except Exception as e:
        logging.error(f"Error loading settings: {str(e)}")
        return None


# Функции для работы с настройками новостей
def save_news_settings(settings):
    try:
        with open(fr"{data_dir}\news_settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка сохранения настроек новостей: {str(e)}")


def load_news_settings():
    try:
        if os.path.exists(fr"{data_dir}\news_settings.json"):
            with open(fr"{data_dir}\news_settings.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка загрузки настроек новостей: {str(e)}")
    return {}


# Функции для работы с настройками новостей
def save_news(news_dict):
    try:
        with open(fr"{data_dir}\news.json", "w", encoding="utf-8") as f:
            json.dump(news_dict, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка сохранения настроек новостей: {str(e)}")


def load_news():
    try:
        if os.path.exists(fr"{data_dir}\news.json"):
            with open(fr"{data_dir}\news.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка загрузки настроек новостей: {str(e)}")
    return {}


def load_language():
    try:
        if os.path.exists(fr"{data_dir}\language.json"):
            with open(fr"{data_dir}\language.json", "r", encoding="utf-8") as f:
                return json.load(f).get("language", "ru")
        else:
            save_language("ru")
            return "ru"
    except Exception:
        return "ru"


def save_language(lang_code):
    try:
        with open(fr"{data_dir}\language.json", "w", encoding="utf-8") as f:
            json.dump({"language": lang_code}, f)
    except Exception as e:
        print(f"Ошибка сохранения языка: {e}")


data_dir = get_or_create_instance_directory()
logs_folder = f"{data_dir}\\logs"
log_dir = f'{user_log_dir(appname, appauthor)}'

if __name__ == '__main__':
    init_dirs()

    # Получаем или создаём уникальную папку
    instance_directory = get_or_create_instance_directory()

    print(f"Этот экземпляр использует папку: {instance_directory}")
