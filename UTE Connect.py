import json
import os
import re
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta

import httpx
import psutil
import pytz
import requests
import telebot
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtCore import QThread, pyqtSignal, QTime, Qt, QRegularExpression, QDate, QTranslator, QLocale
from PyQt5.QtGui import QIcon, QRegularExpressionValidator, QFontMetrics, QFont, QPainter, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QHeaderView, QMessageBox, \
    QLineEdit, QLabel, QGroupBox, QHBoxLayout, QCheckBox, QVBoxLayout, QWidget, QScrollArea, QTimeEdit, QFrame, \
    QGridLayout, QPushButton, QDialog, QSpinBox, QTableWidget, QGraphicsOpacityEffect, QSizePolicy, QAbstractItemView
from flask import Flask, request, abort
from tqdm import tqdm

from disclaimer_text import DisclaimerWindow
from loggingfile import logging
from mm_trading import OptionSeries
from mm_types import MM_MODES
from news import NewsFilterDialog, NewsUpdater
from programm_files import save_money_management_data, load_money_management_data, save_auth_data, \
    load_auth_data, load_statistic_data, CURRENT_VERSION, load_additional_settings_data, save_additional_settings_data, \
    load_news_settings, save_news_settings, load_news, load_language, save_language, logs_folder, \
    save_statistic_data
from rc_icons import qInitResources
from scrollbar_style import scrollbarstyle
from themes import dark_theme, light_theme, blocked_cell, allowed_cell, allowed_color, transparent_text_color, \
    background_color
from utils import recalculate_summary

qInitResources()
API_TOKEN = '7251126188:AAGsTPq2F1bWCJ_9DfSQlMH29W-FXQdWcOA'
CHAT_ID = '-1002258303908'

EXPIRED_DATETIME = datetime(2099, 9, 1)

# Инициализация бота с использованием pyTelegramBotAPI
bot = telebot.TeleBot(API_TOKEN)

app = Flask(__name__)

# Id для сверки
ALLOWED_PARTNER_IDS = ["111-116", "777-13269", "777-1"]

sys.setrecursionlimit(2000)

MM_TABLE_FIELDS = {
    "Тип ММ": 1,
    "Инвестиция": 2,
    "Экспирация": 3,
    "WIN": 4,
    "LOSS": 5,
    # "Результат": 6,
    # "Фильтр выплат": 5,
    "Тейк профит": 6,
    "Стоп лосс": 7,
}

localisations = {
    'ru': QLocale(QLocale.Russian, QLocale.Russia),
    'en': QLocale(QLocale.English, QLocale.UnitedStates)
}


# Синхронная проверка версии
class TelegramBotThread(QThread):
    # Сигнал для обновления UI
    version_check_result = pyqtSignal(dict)

    def __init__(self, chat_id, parent=None):
        super().__init__(parent)
        self.chat_id = chat_id

    def get_last_pinned_message(self):
        # Получаем последнее закрепленное сообщение
        pinned_message = bot.get_chat(self.chat_id).pinned_message
        return pinned_message

    def check_version(self):
        self.version_check_result.emit(
            {"status": True, "message": "Вы используете актуальную версию бота."})
        return

        try:
            pinned_message = self.get_last_pinned_message()
            logging.debug(f"Pinned message: {pinned_message}")
            if not pinned_message:
                self.version_check_result.emit(
                    {"status": False, "message": "Не удалось проверить актуальность версии."})
                return

            pinned_text = pinned_message.text or pinned_message.caption

            # Ищем версию в тексте закрепленного сообщения
            version_pattern = r"#(\d+\.\d+\.\d+)"
            if pinned_text:
                match = re.search(version_pattern, pinned_text)

                if match:
                    pinned_version = match.group(1)
                    logging.debug(f"{pinned_version=} {CURRENT_VERSION=}")
                    if pinned_version > CURRENT_VERSION:
                        self.version_check_result.emit(
                            {"status": False,
                             "message": "Внимание! Ваш бот устарел. Пожалуйста, обновите до последней версии (текущая "
                                        f"версия: {CURRENT_VERSION}, актуальная: {pinned_version})"})

                    else:
                        self.version_check_result.emit(
                            {"status": True, "message": "Вы используете актуальную версию бота."})
                else:
                    self.version_check_result.emit(
                        {"status": False, "message": "Не удалось найти информацию о версии в закрепленном сообщении."})
            else:
                self.version_check_result.emit(
                    {"status": False, "message": "Не удалось найти информацию о версии в закрепленном сообщении."})
        except Exception:
            logging.exception("Exception occurred")

    def run(self):
        self.check_version()


def check_aff(aff_id):
    try:
        if aff_id == '13269':
            return True, ""

        def check(url, user_id, aff_id):
            def remove_first_four_chars(s):
                # Удаляем первые 4 символа
                return s[4:]

            if len(user_id) < 4:
                user_id = "777-11"
            if len(aff_id) < 4:
                aff_id = "777-11"

            # user_id = remove_first_four_chars(user_id)
            aff_id = remove_first_four_chars(aff_id)

            data = {
                'user_id': user_id,
                'aff_id': aff_id
            }
            # Отправляем POST-запрос
            response = requests.post(url, json=data, timeout=4)

            # Проверяем статус-код ответа
            if response.status_code == 200:
                # Обрабатываем ответ
                response_data = response.json()  # Предполагая, что ответ в формате JSON

                if response_data['message'] == 8:
                    return True

                else:
                    return False
            else:
                print(response.text)

            return False

        url_id_pairs = [
            ["777-13269", "https://ultimatetradingexperience.limited/ajax/check_aff_trade_id.php"],
            ["777-116", "https://ultimatetradingexperience.limited/ajax/check_aff_id.php"]
        ]

        rezs = []
        for own_id, url in url_id_pairs:
            rezs.append(check(url, aff_id, own_id))

        if rezs[0] or rezs[1]:
            return True, ""
        elif datetime.now() <= EXPIRED_DATETIME:
            logging.debug("Allow before 1st september")
            return True, ""
        elif datetime.now() > EXPIRED_DATETIME:
            return False, "expired"
        return False, "wrong"
    except Exception as e:
        logging.exception(e)
        return False, "error"


def find_free_port(start_port=80, max_attempts=5):
    """Находит первый свободный порт начиная с start_port."""
    for p in range(start_port, start_port + max_attempts):
        if not is_port_in_use(p):
            return p
    raise RuntimeError("Не удалось найти свободный порт.")


def is_port_in_use(p):
    """Проверяет, используется ли указанный порт."""
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == p:
            return True
    return False


def open_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)

    if sys.platform == 'win32':
        os.startfile(path)
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', path])
    else:  # Linux
        subprocess.Popen(['xdg-open', path])


class FlaskThread(QThread):
    data_received = pyqtSignal(dict)

    def run(self):
        global port
        try:
            auth_data = load_auth_data()
            if auth_data.get("mt4_url"):
                splitted_auth_data = auth_data.get("mt4_url").strip().replace("https://", "").replace("http://",
                                                                                                      "").split(
                    ':')
                if len(splitted_auth_data) == 2:
                    host, _ = splitted_auth_data
                    # port = int(port)
                else:
                    host = splitted_auth_data[0]
            else:
                auth_data["mt4_url"] = "http://127.0.0.1:80"
                save_auth_data(auth_data)
                host = "127.0.0.1"

            # Найти свободный порт
            port = find_free_port()

            print(host, port)
            app.run(host=host, port=port, use_reloader=False, debug=False)
        except Exception:
            logging.exception("Exception occurred")

    def send_data_to_qt(self, data):
        self.data_received.emit(data)


@app.route('/', methods=['GET'])
def query_example():
    pair = request.args.get('pair')
    direct = request.args.get('direct')
    if pair is None or direct is None:
        return abort(400, 'Record not found')

        # Асинхронно дублируем запрос
        async def duplicate():
            duplicate_url = f"http://localhost:{port + 1}/?pair={pair}&direct={direct}"
            try:
                async with httpx.AsyncClient(timeout=0.5) as client:
                    response = await client.get(duplicate_url)
                    print(f"Дубликат успешно отправлен на {duplicate_url}, статус: {response.status_code}")
            except Exception as e:
                traceback.print_exc()
                print(f"Ошибка при дублировании запроса: {e}")

        # Запускаем асинхронный запрос в фоне
        # asyncio.create_task(duplicate())
    # Отправляем данные в основное приложение
    flask_thread.send_data_to_qt({'pair': pair, 'direct': direct})
    print(f"Flask got a signal: {pair}:{direct}")
    return f'{pair}:{direct}'


class MainWindow(QMainWindow):
    def __init__(self, language):
        super().__init__()
        if getattr(sys, 'frozen', False):
            applicationPath = sys._MEIPASS
        elif __file__:
            applicationPath = os.path.dirname(__file__)
        ui_path = os.path.join(applicationPath, 'inteface_W7.ui')
        uic.loadUi(ui_path, self)
        icon_path = os.path.join(applicationPath, 'icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle('UTE Connect')
        QtWidgets.QApplication.instance().focusChanged.connect(self.on_focusChanged)

        # Языки
        self.translator = QtCore.QTranslator()
        self.current_language = lang  # например

        self.startButton.clicked.connect(self.start_client_thread)
        self.stopButton.clicked.connect(self.stop_client_thread)
        self.bot = None
        self.client_socket = None
        self.is_connected = False
        self.last_recv = None

        self.flask_running = False

        # Пример, если хранишь тему в настройках
        settings = load_additional_settings_data()
        self.theme = settings.get("theme", "dark")

        # Режим ММ
        self.selected_mm_mode = 0

        # Статистика
        self.btn_apply.clicked.connect(self.update_all_statistic)  # Привязываем кнопку
        self.delete_stats.clicked.connect(self.delete_statistic)  # Привязываем кнопку

        # Менеджмент
        # Подключаем кнопки к функциям
        self.investment_type = None  # Тип инвестиций (None, "number", "percent")

        self.addButton.clicked.connect(lambda: self.addRow(add_copy=True))
        self.saveButton.clicked.connect(self.saveData)
        self.haveUnsavedRows = False
        self.allowToRunBot = False

        # Регулярное выражение для проверки инвестиции (разрешены цифры и знак %)
        self.investment_validator = QRegularExpressionValidator(QRegularExpression(r"^\d+(\.\d{2})$"))
        self.digit_validator = QRegularExpressionValidator(QRegularExpression(r"^\d+?$"))
        self.expiration_validator = QRegularExpressionValidator(QRegularExpression(r"^(\d{2}:\d{2}:\d{2}|\d+)$"))
        self.type_mm = QRegularExpressionValidator(QRegularExpression(r"\d{1}"))

        self.initManageTable()

        # Дата пикеры
        self.dateTimeEdit_1.setDate(QDate.currentDate().addDays(-99999))  # Устанавливаем текущую дату
        self.dateTimeEdit_1.dateTimeChanged.connect(self.on_datetime_changed)  # Подключаем обработчик

        self.dateTimeEdit_2.setDate(QDate.currentDate().addDays(1))  # Устанавливаем текущую дату
        self.dateTimeEdit_2.dateTimeChanged.connect(self.on_datetime_changed)  # Подключаем обработчик

        # Удаление последней
        self.deleteButton.clicked.connect(self.deleteClicked)
        self.deleteButton.setCursor(Qt.CursorShape.PointingHandCursor)

        # Локализация
        self.dateTimeEdit_1.setLocale(localisations[lang])
        self.dateTimeEdit_2.setLocale(localisations[lang])

        # Проверка версии
        self.check_version()

        self.ACCOUNT_LABELS = {
            'real_rub': self.tr("Реальный RUB"),
            'real_dollar': self.tr("Реальный USD"),
            'demo': self.tr("Демо аккаунт")
        }

        self.STATISCTIC_ACCOUNT_LABELS = {
            'real_rub': self.tr("Реальный RUB"),
            'real_dollar': self.tr("Реальный USD"),
            'demo': self.tr("Демо аккаунт"),
            'any': self.tr("Любой")
        }

        self.language_combo.addItem("Русский", userData="ru")
        self.language_combo.addItem("English", userData="en")
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        self.set_combo_by_data(self.language_combo, lang)



        self.type_account.clear()
        for key, label in self.ACCOUNT_LABELS.items():
            self.type_account.addItem(label, userData=key)

        self.type_account_statistic.clear()
        for key, label in self.STATISCTIC_ACCOUNT_LABELS.items():
            self.type_account_statistic.addItem(label, userData=key)
        self.set_combo_by_data(self.type_account_statistic, 'any')
        # self.type_account.currentData()

        # Создание первой строки
        if not load_money_management_data():
            self.addRow()

        auth_data = load_auth_data()
        if auth_data:
            self.token_edit.setText(auth_data['token'])
            self.userid_edit.setText(auth_data['user_id'])
            self.urlEdit.setText(auth_data['url'])

            self.set_combo_by_data(self.type_account, auth_data['selected_type_account'])
            self.account_type = self.type_account.currentData()
            self.mt4Url.setText(auth_data.get("mt4_url", "http://127.0.0.1"))
            # self.log_message('Данные последней успешной авторизации установлены.')

        # Сохранение таблицы, без уведомления, если успешно
        self.saveData(nide_notification=True)

        self.setStatusBar(None)

        # Добавляем текст поверх всех виджетов
        self.overlay_text = TransparentText(self.tr("Версия") + f': {CURRENT_VERSION}', self, self.theme)
        self.update_text_position()  # Устанавливаем позицию текста

        # self.stats_overlay_time = TransparentText('', self)
        # self.update_time_position()  # Устанавливаем позицию текста

        # Обновляем статистику
        self.btn_apply.click()

        # Данные по новостям
        self.news_data = None

        # Дополнительные настройки
        self.created_additional_settings = False
        if load_additional_settings_data():
            self.createAdditionalSettings({'only_pair_list': 'ok',
                                           'pair_list': {'GBPUSD OTC': {'percent': 90, 'float': 5},
                                                         'AUDUSD OTC': {'percent': 90, 'float': 5},
                                                         'USDJPY OTC': {'percent': 90, 'float': 3},
                                                         'EURUSD OTC': {'percent': 90, 'float': 5},
                                                         'BTCUSDT': {'percent': 82, 'float': 2},
                                                         'GBPNZD': {'percent': 81, 'float': 5},
                                                         'AUDCAD': {'percent': 81, 'float': 5},
                                                         'GBPJPY': {'percent': 81, 'float': 3},
                                                         'NZDCAD': {'percent': 81, 'float': 5},
                                                         'NZDCHF': {'percent': 81, 'float': 5},
                                                         'NZDJPY': {'percent': 81, 'float': 3},
                                                         'NZDUSD': {'percent': 81, 'float': 5},
                                                         'USDCAD': {'percent': 81, 'float': 5},
                                                         'USDCHF': {'percent': 81, 'float': 5},
                                                         'USDJPY': {'percent': 81, 'float': 3},
                                                         'EURAUD': {'percent': 81, 'float': 5},
                                                         'GBPCAD': {'percent': 81, 'float': 5},
                                                         'AUDCHF': {'percent': 81, 'float': 5},
                                                         'AUDJPY': {'percent': 81, 'float': 3},
                                                         'AUDUSD': {'percent': 81, 'float': 5},
                                                         'CADCHF': {'percent': 81, 'float': 5},
                                                         'CADJPY': {'percent': 81, 'float': 3},
                                                         'CHFJPY': {'percent': 81, 'float': 3},
                                                         'EURCAD': {'percent': 81, 'float': 5},
                                                         'EURCHF': {'percent': 81, 'float': 5},
                                                         'EURGBP': {'percent': 81, 'float': 5},
                                                         'EURJPY': {'percent': 81, 'float': 3},
                                                         'EURNZD': {'percent': 81, 'float': 5},
                                                         'EURUSD': {'percent': 81, 'float': 5},
                                                         'GBPAUD': {'percent': 81, 'float': 5},
                                                         'GBPCHF': {'percent': 81, 'float': 5},
                                                         'GBPUSD': {'percent': 50, 'float': 5},
                                                         'EURJPY BO': {'percent': 20, 'float': 3},
                                                         'GBPUSD BO': {'percent': 20, 'float': 5},
                                                         'GBPCAD BO': {'percent': 20, 'float': 5},
                                                         'GBPCHF BO': {'percent': 20, 'float': 5},
                                                         'NZDCHF BO': {'percent': 20, 'float': 5},
                                                         'NZDJPY BO': {'percent': 20, 'float': 3},
                                                         'NZDUSD BO': {'percent': 20, 'float': 5},
                                                         'USDCHF BO': {'percent': 20, 'float': 5}}})


        # Инициализация новостного обновления

        self.news_settings = load_news_settings()
        if self.news_settings.get('enabled') is True:
            self.news_filter_enabled = True
        else:
            self.news_filter_enabled = False

        self.language = language
        self.news_updater = NewsUpdater(self, self.language)

        self.news_update_timer = QtCore.QTimer(self)
        self.news_update_timer.timeout.connect(self.updateNewsTable)
        self.news_update_timer.start(10000)

        self.text_update_timer = QtCore.QTimer(self)
        self.text_update_timer.timeout.connect(self.updateTransParentTime)
        self.text_update_timer.start(1000)

        self.fix_table()

        self.trading_paused = False

        # Отключаем кнопку стоп
        self.stopButton.setEnabled(False)
        self.change_widget_opacity(self.stopButton, 50)

        self.logsButton.clicked.connect(lambda: open_folder(logs_folder))

        # Новые элементы управления
        self.toggleSummaryButton.clicked.connect(self.toggle_summary)
        self.stats_stats_overlay_time = self.findChild(QLabel, "stats_stats_overlay_time")

        # Изначально сводка видна
        self.toggleSummaryButton.setText(self.tr("Скрыть сводку"))

        # Тема Theme
        self.theme_combo.addItem(self.tr("Тёмная"), userData="dark")
        self.theme_combo.addItem(self.tr("Светлая"), userData="light")
        self.theme_combo.currentIndexChanged.connect(self.switch_theme)


        index = self.theme_combo.findData(self.theme)
        if index != -1:
            self.theme_combo.setCurrentIndex(index)
        self.switch_theme()  # Применить стиль

        self.setMinimumSize(1360, 600)
        self.resize(1360, 600)  # ← Это заставляет окно запуститься в минимальном размере

        self.update_mm_table(self.selected_mm_mode)

        # Показываем окно отказа от ответственности при старте
        self.disclaimer_timer = QtCore.QTimer(self)
        self.disclaimer_timer.timeout.connect(self.show_disclaimer)
        self.disclaimer_timer.start(1000)

    def show_disclaimer(self):
        # Создаём и отображаем окно отказа
        self.disclaimer = DisclaimerWindow()
        self.disclaimer.show()
        self.disclaimer.setFocus()
        self.disclaimer_timer.stop()

    def switch_theme(self):
        self.theme = self.theme_combo.currentData()

        # Применяем стили ко всему приложению
        if self.theme == 'light':
            style_str = light_theme
        else:
            style_str = dark_theme

        # Применяем стили ко всему приложению
        QApplication.instance().setStyleSheet(style_str)

        # Для таблиц нужны дополнительные настройки
        self.fix_table_style(self.theme)

        # Сохраняем в настройках
        add_settings = load_additional_settings_data()
        add_settings["theme"] = self.theme
        save_additional_settings_data(add_settings)

        self.btn_apply.click()

        if hasattr(self, "manage_table"):
            self.manage_table.setRowCount(0)
            self.initManageTable()
            self.saveData(nide_notification=True)

        self.overlay_text.setStyleSheet(f"color: {transparent_text_color(self.theme)};")


        if self.theme == 'light':
            style_str = light_theme
        else:
            style_str = dark_theme

        self.main_scroll_container.setStyleSheet(f"QWidget {{ border: none; background-color: {background_color(self.theme)}; }} " + style_str)

    def fix_table_style(self, theme):
        """Дополнительные настройки стилей для таблиц"""
        if theme == 'light':
            table_style = """
                QTableWidget {
                    background: white;
                    color: black;
                    border: 1px solid #dddddd;
                }
                QHeaderView::section {
                    background-color: #f0f0f0;
                    color: black;
                    border: 1px solid #dddddd;
                }
            """
            header_style = """
                QHeaderView::section {
                    background-color: #f0f0f0;
                    color: black;
                    border: 1px solid #dddddd;
                }
            """
        else:
            table_style = """
                QTableWidget {
                    background: rgb(12,17,47);
                    color: white;
                    border: 1px solid rgb(18, 26, 61);
                }
                QHeaderView::section {
                    background-color: rgb(18, 26, 61);
                    color: white;
                    border: 1px solid rgb(18, 26, 61);
                }
            """
            header_style = """
                QHeaderView::section {
                    background-color: rgb(18, 26, 61);
                    color: white;
                    border: 1px solid rgb(18, 26, 61);
                }
            """

        # Применяем стили к таблицам
        self.manage_table.setStyleSheet(table_style)
        self.trades_table.setStyleSheet(table_style)
        self.textBrowser.setStyleSheet(table_style)

        # Применяем стили к заголовкам
        self.manage_table.horizontalHeader().setStyleSheet(header_style)
        self.trades_table.horizontalHeader().setStyleSheet(header_style)

        # Для новостной таблицы, если она есть
        if hasattr(self, 'news_table'):
            self.news_table.setStyleSheet(table_style)
            self.news_table.horizontalHeader().setStyleSheet(header_style)

        # Скроллинг
        self.trades_table.setStyleSheet(scrollbarstyle(margins=True, theme=self.theme))
        self.manage_table.setStyleSheet(scrollbarstyle(theme=self.theme))
        self.textBrowser.setStyleSheet(scrollbarstyle(theme=self.theme))
        if hasattr(self, 'add_scroll_area'):
            self.add_scroll_area.setStyleSheet(scrollbarstyle(theme=self.theme))

        self.textBrowser.setOpenExternalLinks(True)


    def toggle_summary(self):
        """Переключает отображение сводки статистики"""
        if self.summary_table.isVisible():
            # Скрываем сводку и метку времени
            self.summary_table.hide()
            self.stats_overlay_time.hide()

            # Сдвигаем элементы влево
            self.move_widgets_left()

            # Расширяем таблицу сделок на всю ширину
            self.gridLayout_6.addWidget(self.trades_table, 1, 0, 3, 10)
            self.toggleSummaryButton.setText("Показать сводку")
        else:
            # Показываем сводку и метку времени
            self.summary_table.show()
            self.stats_overlay_time.show()

            # Возвращаем элементы на место
            self.move_widgets_right()

            # Возвращаем таблицу сделок в исходное положение
            self.gridLayout_6.addWidget(self.trades_table, 1, 1, 3, 9)
            self.toggleSummaryButton.setText("Скрыть сводку")

    def set_combo_by_data(self, combo_box: QtWidgets.QComboBox, value):
        index = combo_box.findData(value)
        if index != -1:
            combo_box.setCurrentIndex(index)

    def move_widgets_left(self):
        """Сдвигает элементы управления влево при скрытии сводки"""
        # Кнопка "Скрыть сводку" -> из (0,6) в (0,5)
        self.gridLayout_6.addWidget(self.toggleSummaryButton, 0, 0)

        # DateTimePicker 1 -> из (0,4) в (0,3)
        self.gridLayout_6.addWidget(self.dateTimeEdit_1, 0, 4)

        # DateTimePicker 2 -> из (0,5) в (0,4)
        self.gridLayout_6.addWidget(self.dateTimeEdit_2, 0, 5)

        # ComboBox типа аккаунта -> из (0,1-2) в (0,0-1)
        self.gridLayout_6.addWidget(self.type_account_statistic, 0, 1, 1, 2)

    def move_widgets_right(self):
        """Возвращает элементы управления на место при показе сводки"""
        # Кнопка "Скрыть сводку" -> обратно в (0,6)
        self.gridLayout_6.addWidget(self.toggleSummaryButton, 0, 1)

        # DateTimePicker 1 -> обратно в (0,4)
        self.gridLayout_6.addWidget(self.dateTimeEdit_1, 0, 5)

        # DateTimePicker 2 -> обратно в (0,5)
        self.gridLayout_6.addWidget(self.dateTimeEdit_2, 0, 6)

        # ComboBox типа аккаунта -> обратно в (0,1-2)
        self.gridLayout_6.addWidget(self.type_account_statistic, 0, 2, 1, 2)

    def on_language_changed(self):
        lang_code = self.language_combo.currentData()
        current_lang = load_language()

        if lang_code != current_lang:
            save_language(lang_code)
            QMessageBox.information(
                self,
                self.tr("Требуется перезапуск"),
                self.tr("Изменение языка вступит в силу после перезапуска приложения.")
            )

    def clear_overlay_labels(self, parent_widget: QWidget):
        """
        Удаляет все QLabel, добавленные как дочерние элементы к viewport (например, QTableWidget).
        Предполагается, что такие QLabel добавлялись как наложенные тексты.
        """
        try:
            for child in parent_widget.viewport().findChildren(QLabel):
                child.deleteLater()
        except Exception:
            traceback.print_exc()

    def add_background_text(self, table_widget: QTableWidget, text: str, color: str) -> QLabel:
        self.warn_label = QLabel(text, table_widget.viewport())
        self.warn_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 24px;
                font-style: italic;
                font-weight: bold;
                background: transparent;
            }}
        """)
        self.warn_label.setAlignment(Qt.AlignCenter)
        self.warn_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.warn_label.resize(table_widget.viewport().size())
        self.warn_label.show()

        # Обновление позиции при изменении размера таблицы
        def resize_event(event):
            if hasattr(self, 'warn_label'):
                self.warn_label.resize(table_widget.viewport().size())
                QLabel.resizeEvent(self.warn_label, event)

        table_widget.resizeEvent = resize_event

        # Слушаем скроллинг: вертикальный и горизонтальный
        def update_label_geometry():
            if hasattr(self, 'warn_label'):
                self.warn_label.resize(table_widget.viewport().size())
                self.warn_label.move(0, 0)  # Центр всегда будет по центру viewport

        table_widget.verticalScrollBar().valueChanged.connect(update_label_geometry)
        table_widget.horizontalScrollBar().valueChanged.connect(update_label_geometry)

        # Также — обновлять при любом wheel-событии (вдруг нужно)
        def wheel_event(event):
            update_label_geometry()
            QTableWidget.wheelEvent(table_widget, event)  # не забываем вызвать оригинальное поведение

        table_widget.wheelEvent = wheel_event

        return self.warn_label

    def updateTransParentTime(self):
        current_time = datetime.now(pytz.utc)
        current_time = current_time.astimezone(pytz.timezone('Etc/GMT-3'))
        f = current_time.strftime("%d-%m-%Y %H:%M:%S")
        if hasattr(self.bot, "ping") and self.bot.ping is not None:
            self.stats_overlay_time.setText(self.tr("Дата и время (МСК):") + f" {f} " + self.tr("Пинг:") + f" {self.bot.ping} ms")
        else:
            self.stats_overlay_time.setText(self.tr("Дата и время (МСК):") + f" {f}")
        self.stats_overlay_time.setStyleSheet(f"font-weight: bold; color: {transparent_text_color(self.theme)};")

    @QtCore.pyqtSlot("QWidget*", "QWidget*")
    def on_focusChanged(self, old, now):
        try:
            if self.token_edit == now:
                self.token_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            elif self.token_edit == old:
                self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        except Exception:
            traceback.print_exc()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_text_position()  # Обновляем позицию текста при изменении размера окна
        self.update_text_position()  # Обновляем позицию текста при изменении размера окна
        # self.update_time_position()  # Обновляем позицию текста при изменении размера окна

    def update_text_position(self):
        """Обновляет позицию текста внизу окна."""
        text_height = self.overlay_text.height()
        window_height = self.height()

        # Располагаем текст снизу, по центру
        x = 15
        y = window_height - text_height - 15  # Отступ в 10 пикселей от нижнего края
        self.overlay_text.move(x, y)

    def update_time_position(self):
        """Обновляет позицию текста внизу окна."""
        text_height = self.stats_overlay_time.height()
        self.stats_overlay_time.setMinimumWidth(220)
        window_height = self.height()

        # Располагаем текст снизу, по центру
        x = 100
        y = window_height - text_height - 15  # Отступ в 10 пикселей от нижнего края
        self.stats_overlay_time.move(x, y)

    def update_news_filter_warn_position(self):
        """Обновляет позицию текста внизу окна."""
        text_height = self.stats_overlay_time.height()
        self.stats_overlay_time.setMinimumWidth(220)
        window_height = self.height()

        # Располагаем текст снизу, по центру
        x = 100
        y = window_height - text_height - 15  # Отступ в 10 пикселей от нижнего края
        self.stats_overlay_time.move(x, y)

    def fix_table(self):
        # на windows 10 они отображаются не корректно
        self.manage_table.setFrameStyle(QFrame.NoFrame)
        self.manage_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.manage_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)


        self.trades_table.setFrameStyle(QFrame.NoFrame)
        self.trades_table.setStyleSheet(scrollbarstyle(margins=True, theme=self.theme))
        self.trades_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.trades_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.textBrowser.setFrameStyle(QFrame.NoFrame)


        if hasattr(self, 'news_table'):
            self.news_table.setFrameStyle(QFrame.NoFrame)
            self.news_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.news_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)


    # Проверка версии
    def check_version(self):
        try:
            # Запускаем проверку в отдельном потоке
            telegram_thread.version_check_result.connect(self.show_warning)
            telegram_thread.start()
        except:
            logging.exception("Exception occurred")

    def show_warning(self, callback_dict):
        status, message = callback_dict["status"], callback_dict["message"]
        # Используем QMessageBox для отображения предупреждения
        if status is False:
            QMessageBox.critical(self, self.tr("Проверка версии"), message, QMessageBox.StandardButton.Close)
            self.close()

    def createAdditionalSettings(self, pairs):
        if self.created_additional_settings:
            return

        # Удаляем существующий textEdit
        if hasattr(self, 'niggalabel'):
            self.niggalabel.deleteLater()
            del self.niggalabel

        # Загружаем сохраненные настройки
        self.settings = load_additional_settings_data()

        # Создаем основной контейнер с прокруткой
        self.main_scroll_container = QWidget()

        main_layout = QVBoxLayout(self.main_scroll_container)

        # Создаем область прокрутки
        self.add_scroll_area = QScrollArea()
        self.add_scroll_area.setMinimumWidth(350)
        self.add_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.add_scroll_area.setWidgetResizable(True)
        self.add_scroll_area.setStyleSheet(scrollbarstyle(theme=self.theme))
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # 1. Блок новостей
        self.addNewsBlock(scroll_layout)

        # 2. Блок с валютными парами (3 столбца)
        pairs_layout = QVBoxLayout()
        pairs_group_title = QLineEdit()
        pairs_group_title.setText(self.tr("Разрешенные валютные пары"))
        pairs_group_title.setStyleSheet("font-size: 14px; border: none;")
        pairs_layout.addWidget(pairs_group_title)

        # Создаем сетку для 3 столбцов
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)

        self.pair_checkboxes = {}
        row, col = 0, 0
        max_cols = 3

        for pair in pairs["pair_list"]:
            cb = QCheckBox(pair)
            # Восстанавливаем состояние из сохраненных настроек
            if self.settings and "pairs" in self.settings and pair in self.settings["pairs"]:
                cb.setChecked(self.settings["pairs"][pair])
            else:
                if pair.endswith("BO") or pair.endswith("OTC"):
                    cb.setChecked(False)  # По умолчанию включено для других
                else:
                    cb.setChecked(True)  # По умолчанию включено для обычных

            cb.stateChanged.connect(self.onAdditionalSettingsChanged)
            grid_layout.addWidget(cb, row, col)
            self.pair_checkboxes[pair] = cb

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Добавляем сетку в пары
        pairs_layout.addWidget(grid_widget)
        scroll_layout.addLayout(pairs_layout)

        # 3. Блок с расписанием торговли (несколько интервалов)
        schedule_layout = QVBoxLayout()
        schedule_group_title = QLineEdit()
        schedule_group_title.setText(self.tr("Расписание торговли (по МСК)"))
        schedule_group_title.setStyleSheet("font-size: 14px;border: none;")
        schedule_layout.addWidget(schedule_group_title)

        self.schedule_settings = {}
        self.weekdays = [self.tr("Пн"), self.tr("Вт"), self.tr("Ср"), self.tr("Чт"), self.tr("Пт"), self.tr("Сб"),
                         self.tr("Вс")]

        # Создаем виджет для каждого дня
        for day_index, day in enumerate(self.weekdays):
            day_group = QGroupBox(day)
            day_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid gray;
                    border-radius: 5px;
                    margin-top: 1ex;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px 0 3px;
                }
            """)
            day_layout = QVBoxLayout(day_group)

            # Чекбокс для включения дня
            enabled_cb = QCheckBox(self.tr("Активен"))
            enabled_cb.setStyleSheet("margin-bottom: 10px;")

            # Восстанавливаем состояние дня
            day_enabled = True
            if self.settings and "schedule" in self.settings:
                day_settings = self.settings["schedule"][str(day_index)]
                enabled_cb.setChecked(day_settings["enabled"])
                day_enabled = day_settings["enabled"]
            else:
                enabled_cb.setChecked(True)

            # Контейнер для интервалов
            intervals_container = QWidget()
            intervals_layout = QVBoxLayout(intervals_container)

            # Список интервалов
            intervals = []
            if self.settings and "schedule" in self.settings:
                intervals = self.settings["schedule"][str(day_index)]["intervals"]
            else:
                intervals = [{"start": "09:00", "end": "18:00"}]  # По умолчанию

            interval_widgets = []

            # Создаем виджеты для каждого интервала
            for interval in intervals:
                interval_widget = QWidget()
                interval_layout = QHBoxLayout(interval_widget)
                interval_layout.setContentsMargins(0, 0, 0, 5)

                # Поля времени
                start_time = QTimeEdit()
                start_time.setStyleSheet("""
                    QTimeEdit {
                        font-size: 14px;
                    }
                    QTimeEdit::up-button, QTimeEdit::down-button {
                        display: none;
                        width: 0px;
                    }
                """)
                start_time.setDisplayFormat("HH:mm")
                start_time.setEnabled(day_enabled)
                start_time.setTime(QTime.fromString(interval["start"], "HH:mm"))

                end_time = QTimeEdit()
                end_time.setStyleSheet("""
                    QTimeEdit {
                        font-size: 14px;
                    }
                    QTimeEdit::up-button, QTimeEdit::down-button {
                        display: none;
                        width: 0px;
                    }
                """)
                end_time.setDisplayFormat("HH:mm")
                end_time.setEnabled(day_enabled)
                end_time.setTime(QTime.fromString(interval["end"], "HH:mm"))

                # Кнопка удаления интервала
                delete_btn = QPushButton("✕")
                delete_btn.setStyleSheet("""
                    QPushButton {
                        font-size: 12px;
                        min-width: 20px;
                        max-width: 20px;
                        min-height: 20px;
                        max-height: 20px;
                        border-radius: 10px;
                    }
                """)
                delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)

                interval_layout.addWidget(QLabel(self.tr("От:")))
                interval_layout.addWidget(start_time)
                interval_layout.addWidget(QLabel(self.tr("До:")))
                interval_layout.addWidget(end_time)
                interval_layout.addWidget(delete_btn)
                interval_layout.addStretch()

                intervals_layout.addWidget(interval_widget)
                interval_widgets.append({
                    "widget": interval_widget,
                    "start_time": start_time,
                    "end_time": end_time,
                    "delete_btn": delete_btn
                })

            # Кнопка добавления нового интервала
            add_btn = QPushButton(self.tr('+ Добавить интервал'))

            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            day_layout.addWidget(enabled_cb)
            day_layout.addWidget(intervals_container)
            day_layout.addWidget(add_btn)

            schedule_layout.addWidget(day_group)

            # Сохраняем настройки для дня
            self.schedule_settings[day] = {
                "enabled_cb": enabled_cb,
                "intervals_container": intervals_container,
                "intervals_layout": intervals_layout,
                "intervals": interval_widgets,
                "add_btn": add_btn
            }

            # Подключаем обработчики
            enabled_cb.stateChanged.connect(lambda state, d=day: self.toggle_day_enabled(d, state))
            add_btn.clicked.connect(lambda _, d=day: self.add_interval(d))

            # Подключаем обработчики для каждого интервала
            for interval in interval_widgets:
                interval["start_time"].timeChanged.connect(self.onAdditionalSettingsChanged)
                interval["end_time"].timeChanged.connect(self.onAdditionalSettingsChanged)
                interval["delete_btn"].clicked.connect(
                    lambda _, i=interval, d=day: self.remove_interval(d, i)
                )

        scroll_layout.addLayout(schedule_layout)

        # Устанавливаем содержимое в область прокрутки
        self.add_scroll_area.setWidget(scroll_content)
        main_layout.addWidget(self.add_scroll_area)

        # Устанавливаем контейнер в sideSettings
        self.sideSettings.addWidget(self.main_scroll_container)

        self.created_additional_settings = True

        # Если настроек не было, сохраняем значения по умолчанию
        if not self.settings:
            self.onAdditionalSettingsChanged()

        self.fix_table()


        self.updateNewsTable()
        if self.news_data is None:
            self.place_news_loading_text()

        self.place_news_warning_text()

    def news_table_clicked(self):
        return
        row = self.news_table.currentRow()
        col = self.news_table.currentColumn()
        if col == 5:
            self.news_table.setRowHeight(row, 60)

        # value = self.news_table.item(row, col)

    def place_news_warning_text(self):
        self.clear_overlay_labels(self.news_table)
        if self.news_data:
            if self.news_filter_enabled:
                try:
                    if hasattr(self, 'warn_label'):
                        self.warn_label.setParent(None)
                        del self.warn_label
                except Exception:
                    traceback.print_exc()
            else:
                self.add_background_text(self.news_table, self.tr('Внимание!') + "\n" + self.tr('Фильтр выключен!'),
                                         color='red')
        else:
            self.place_news_loading_text()

    def place_news_loading_text(self):
        self.add_background_text(self.news_table, self.tr("Загрузка..."), color='white')

    def addNewsBlock(self, parent_block):
        """Добавляет блок новостей в интерфейс"""
        news_group = QGroupBox()
        self.news_layout = QVBoxLayout(news_group)
        news_group_title = QLineEdit()
        news_group_title.setText(self.tr("Новостной фильтр"))
        news_group_title.setStyleSheet("font-size: 14px;border: none;")
        self.news_layout.addWidget(news_group_title)

        # Таблица новостей
        self.news_table = QTableWidget()
        self.news_table.setMinimumHeight(300)
        self.news_table.setColumnCount(6)
        self.news_table.setHorizontalHeaderLabels([
            self.tr("До"), self.tr("После"), self.tr("Время"),
            self.tr("Важность"), self.tr("Валюта"), self.tr("Событие")
        ])
        self.news_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.news_table.verticalHeader().setVisible(False)
        self.news_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.news_table.setColumnWidth(0, 50)
        self.news_table.setColumnWidth(1, 50)
        self.news_table.setColumnWidth(2, 65)
        self.news_table.setColumnWidth(3, 80)
        self.news_table.setColumnWidth(4, 50)

        self.news_table.cellClicked.connect(self.news_table_clicked)

        self.news_layout.addWidget(self.news_table)

        # Кнопки управления
        buttons_layout = QHBoxLayout()

        self.news_filter_toggle = QPushButton(self.tr("Включить фильтр"))
        self.news_filter_toggle.setStyleSheet("""
        background-color: #121a3d;
        border-radius: 5px;
            padding: 8px;
            font-size: 12px;
        """)
        self.news_filter_toggle.setCheckable(True)
        self.news_filter_toggle.setChecked(False)
        self.news_filter_toggle.toggled.connect(self.toggleNewsFilter)
        buttons_layout.addWidget(self.news_filter_toggle)

        self.news_settings_btn = QPushButton(self.tr("Настройка фильтра"))

        self.news_settings_btn.clicked.connect(self.openNewsFilterSettings)
        buttons_layout.addWidget(self.news_settings_btn)

        self.news_layout.addLayout(buttons_layout)

        # Добавляем в основной layout
        parent_block.addWidget(news_group)

        self.toggleNewsFilter()


    def toggleStyleSheetNewsFilterButton(self, enabled):
        if enabled:
            self.news_filter_toggle.setStyleSheet("""
                            QPushButton {
            background-color: #a83e3e;
            color: white;
            border-radius: 5px;
            padding: 8px;
            font-size: 12px;
        }

        QPushButton:hover {
            background-color: #922f2f; /* чуть темнее */
        }

        QPushButton:pressed {
            background-color: #7a2424; /* ещё темнее при нажатии */
            padding-top: 9px;
            padding-bottom: 7px;
        }

                            """)
        else:
            self.news_filter_toggle.setStyleSheet("""
                            QPushButton {
            background-color: rgb(83, 140, 85);
            color: white;
            border-radius: 5px;
            padding: 8px;
            font-size: 12px;
        }

        QPushButton:hover {
            background-color: rgb(73, 120, 75); /* чуть темнее */
        }

        QPushButton:pressed {
            background-color: rgb(63, 100, 65); /* еще темнее при нажатии */
            padding-top: 9px;
            padding-bottom: 7px;
        }

                            """)

    def updateNewsTable(self):
        if not hasattr(self, "news_table"):
            return

        try:
            news_data = load_news()
            """Обновляет таблицу новостей полученными данными"""
            # Сохраняем текущие настройки перед обновлением
            current_settings = {}
            if hasattr(self, 'news_data'):
                for row in range(self.news_table.rowCount()):
                    news_id = self.news_data[row]['id']
                    current_settings[news_id] = {
                        'before': self.news_table.cellWidget(row, 0).value(),
                        'after': self.news_table.cellWidget(row, 1).value()
                    }
            # Обновляем данные
            self.news_table.setRowCount(len(news_data))
            for row, news in enumerate(news_data):
                news_id = news['id']

                # Время До
                before_spin = QSpinBox()
                before_spin.setRange(0, 1440)

                # Восстанавливаем предыдущие настройки, если они есть
                if news_id in current_settings:
                    before_spin.setValue(current_settings[news_id]['before'])
                else:
                    before_spin.setValue(self.news_settings.get(str(news_id), {}).get('before', 0))

                before_spin.valueChanged.connect(
                    lambda value, news_idd=news_id: self.updateNewsSetting(news_idd, 'before', value)
                )

                self.news_table.setCellWidget(row, 0, before_spin)

                # Время После
                after_spin = QSpinBox()
                after_spin.setRange(0, 1440)

                if news_id in current_settings:
                    after_spin.setValue(current_settings[news_id]['after'])
                else:
                    after_spin.setValue(self.news_settings.get(str(news_id), {}).get('after', 0))
                after_spin.valueChanged.connect(
                    lambda value, id=news_id: self.updateNewsSetting(id, 'after', value)
                )

                self.news_table.setCellWidget(row, 1, after_spin)

                # Остальные поля
                self.news_table.setItem(row, 2, QTableWidgetItem(news['time']))
                self.news_table.setItem(row, 3, QTableWidgetItem(news['importance']))
                self.news_table.setItem(row, 4, QTableWidgetItem(news['currency']))
                self.news_table.setItem(row, 5, QTableWidgetItem(news['event']))

                self.news_table.setRowHeight(row, 30)

            # Сохраняем данные для фильтрации
            self.news_data = news_data

            self.place_news_warning_text()

        except Exception:
            traceback.print_exc()

    def updateNewsSetting(self, news_id, setting, value):
        """Обновляет настройку для конкретной новости"""
        if not hasattr(self, 'news_settings'):
            self.news_settings = {}

        if news_id not in self.news_settings:
            self.news_settings[news_id] = {}

        self.news_settings[news_id][setting] = value
        save_news_settings(self.news_settings)

    def toggleNewsFilter(self, enabled=None):
        """Переключает состояние новостного фильтра"""

        # Если ручной запуску ф-и то данные берем из настроек:
        if enabled is None:
            self.news_settings = load_news_settings()

            enabled = self.news_settings.get("enabled")

        self.news_filter_toggle.setText(self.tr("Выключить фильтр") if enabled else self.tr("Включить фильтр"))

        self.toggleStyleSheetNewsFilterButton(enabled)

        self.news_filter_enabled = enabled
        self.news_settings["enabled"] = enabled
        save_news_settings(self.news_settings)

        self.place_news_warning_text()

        # Если фильтр включен, сразу обновляем новости

    def openNewsFilterSettings(self):
        """Открывает диалог настройки новостного фильтра"""
        dialog = NewsFilterDialog(self.news_settings.get('filter_settings', {}))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            filter_settings = dialog.get_settings()
            self.news_settings['filter_settings'] = filter_settings
            save_news_settings(self.news_settings)
            dialog.close()

    def isInNewsBlackout(self, pair):
        """Проверяет, попадает ли текущее время в новостной блэкаут"""
        if not hasattr(self, 'news_filter_enabled') or not self.news_filter_enabled:
            return False, None

        if not hasattr(self, 'news_data') or not self.news_data:
            return False, None

        # Текущее время
        now = datetime.now(pytz.timezone('Etc/GMT-3'))

        target_news = None

        for news in self.news_data:
            # Получаем настройки
            news_id = str(news['id'])

            filter_settings = self.news_settings.get('filter_settings', {})

            # Пропускаем новости без настроек
            if self.news_settings.get(str(news['id'])):


                settings = self.news_settings.get(news_id, {})
                before_min = settings.get('before', 0)
                after_min = settings.get('after', 0)

            elif filter_settings:
                # Переопределяем настройками фильтра по важности

                importance = news.get('importance', '').lower()
                if importance == 'low':
                    before_min = filter_settings.get('low_before', 0)
                    after_min = filter_settings.get('low_after', 0)
                elif importance == 'medium':
                    before_min = filter_settings.get('med_before', 0)
                    after_min = filter_settings.get('med_after', 0)
                elif importance == 'high':
                    before_min = filter_settings.get('high_before', 0)
                    after_min = filter_settings.get('high_after', 0)
                else:
                    logging.warning(f"Не известная {importance=}")
                    continue

            else:
                continue

            # Пропуск если интервалы не заданы
            if before_min == 0 and after_min == 0:
                continue

            # Формируем время новости
            try:
                tz = pytz.timezone('Etc/GMT-3')
                news_time = tz.localize(datetime.strptime(f"{now.date()} {news['time']}", "%Y-%m-%d %H:%M"))
            except Exception as e:
                print(f"Ошибка парсинга времени новости: {e}")
                continue

            # Период блэкаута
            start_time = news_time - timedelta(minutes=before_min)
            end_time = news_time + timedelta(minutes=after_min)

            if start_time <= now <= end_time:
                print(
                    f"Попадание в блэкаут по новости ID {news_id} ({news.get('currency')}, важность: {news.get('importance')})")
                print(f"Текущее время: {now}, Блэкаут: с {start_time} до {end_time}")
                target_news = news
                only_currency = filter_settings.get('only_currency', False)
                reverse_filter = filter_settings.get('reverse_filter', False)

                if only_currency:
                    if news.get('currency') and news['currency'] in pair:
                        print(f"Валюта {news['currency']} найдена в паре {pair}")
                        print(f"Результат с учётом reverse_filter: {not reverse_filter}")
                        return not reverse_filter, target_news
                    else:
                        print(f"Валюта {news.get('currency')} не найдена в паре {pair}, продолжаем")
                        continue

                print(f"Результат без валютной фильтрации: {not reverse_filter}")
                return not reverse_filter, target_news

        reverse = self.news_settings.get('filter_settings', {}).get('reverse_filter', False)
        print(f"Не найдено актуальных новостей в блэкауте. Возвращаем reverse_filter: {reverse}")
        return reverse, target_news

    def toggle_day_enabled(self, day, state):
        """Включает/выключает все элементы дня"""
        day_settings = self.schedule_settings[day]
        for interval in day_settings["intervals"]:
            interval["start_time"].setEnabled(state)
            interval["end_time"].setEnabled(state)
        self.onAdditionalSettingsChanged()

    def add_interval(self, day):
        """Добавляет новый временной интервал для дня"""
        day_settings = self.schedule_settings[day]

        # Создаем новый виджет интервала
        interval_widget = QWidget()
        interval_layout = QHBoxLayout(interval_widget)
        interval_layout.setContentsMargins(0, 0, 0, 5)

        # Поля времени (по умолчанию последнее время + 30 минут)
        last_end_time = QTime(9, 0)
        if day_settings["intervals"]:
            last_end_time = day_settings["intervals"][-1]["end_time"].time().addSecs(1800)

        start_time = QTimeEdit()
        start_time.setStyleSheet("""
            QTimeEdit {
                font-size: 14px;
            }
            QTimeEdit::up-button, QTimeEdit::down-button {
                display: none;
                width: 0px;
            }
        """)
        start_time.setDisplayFormat("HH:mm")
        start_time.setEnabled(day_settings["enabled_cb"].isChecked())
        start_time.setTime(last_end_time)

        end_time = QTimeEdit()
        end_time.setStyleSheet("""
            QTimeEdit {
                font-size: 14px;
            }
            QTimeEdit::up-button, QTimeEdit::down-button {
                display: none;
                width: 0px;
            }
        """)
        end_time.setDisplayFormat("HH:mm")
        end_time.setEnabled(day_settings["enabled_cb"].isChecked())
        end_time.setTime(last_end_time.addSecs(3600))  # +1 час

        # Кнопка удаления
        delete_btn = QPushButton("✕")
        delete_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px
                border-radius: 10px;
            }
        """)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        interval_layout.addWidget(QLabel(self.tr("От:")))
        interval_layout.addWidget(start_time)
        interval_layout.addWidget(QLabel(self.tr("До:")))
        interval_layout.addWidget(end_time)
        interval_layout.addWidget(delete_btn)
        interval_layout.addStretch()

        # Добавляем в контейнер
        day_settings["intervals_layout"].addWidget(interval_widget)

        # Сохраняем в настройках
        interval_data = {
            "widget": interval_widget,
            "start_time": start_time,
            "end_time": end_time,
            "delete_btn": delete_btn
        }
        day_settings["intervals"].append(interval_data)

        # Подключаем обработчики
        start_time.timeChanged.connect(self.onAdditionalSettingsChanged)
        end_time.timeChanged.connect(self.onAdditionalSettingsChanged)
        delete_btn.clicked.connect(lambda _, i=interval_data, d=day: self.remove_interval(d, i))

        self.onAdditionalSettingsChanged()

    def remove_interval(self, day, interval):
        """Удаляет временной интервал"""
        day_settings = self.schedule_settings[day]

        # Удаляем из интерфейса
        interval["widget"].deleteLater()

        # Удаляем из списка
        day_settings["intervals"] = [i for i in day_settings["intervals"] if i != interval]

        self.onAdditionalSettingsChanged()

    def onAdditionalSettingsChanged(self):
        # Собираем данные по парам
        pairs_settings = {}
        for pair, cb in self.pair_checkboxes.items():
            pairs_settings[pair] = cb.isChecked()

        # Собираем данные по расписанию
        schedule_settings = {}
        for day, day_settings in self.schedule_settings.items():
            intervals = []
            for interval in day_settings["intervals"]:
                intervals.append({
                    "start": interval["start_time"].time().toString("HH:mm"),
                    "end": interval["end_time"].time().toString("HH:mm")
                })

            schedule_settings[str(self.weekdays.index(day))] = {
                "enabled": day_settings["enabled_cb"].isChecked(),
                "intervals": intervals
            }

        # Сохраняем настройки
        settings = {
            "pairs": pairs_settings,
            "schedule": schedule_settings
        }
        self.settings = settings
        save_additional_settings_data(settings)

    def ute_connect(self):
        token = self.token_edit.text()
        user_id = self.userid_edit.text()
        url = self.urlEdit.text()
        auth_data = {
            "selected_type_account": self.type_account.currentData(),
            "token": self.token_edit.text().strip(),
            "user_id": self.userid_edit.text().strip(),
            "url": self.urlEdit.text().strip(),
            "mt4_url": self.mt4Url.text().strip()
        }
        save_auth_data(auth_data)
        verified = False

        if self.bot is None:
            # Добавлен метод проверки партнерского ID
            try:
                self.bot = OptionSeries(url=url, token=token, userid=user_id, auth_data=load_auth_data(), window=self)

                for answer_text in self.bot.serv_answ:
                    if answer_text is False:
                        continue

                    if "Connection successful" in str(answer_text):
                        self.log_message(self.tr("Соединение установлено"))
                        if hasattr(self.bot, 'pair_list'):
                            self.createAdditionalSettings(self.bot.pair_list)

                    else:
                        self.log_message(answer_text)
                    if "partner_id" not in answer_text:
                        continue
                    d = json.loads(answer_text)
                    if d["partner_id"] in ALLOWED_PARTNER_IDS:
                        verified = True
            except Exception:
                error_text = traceback.format_exc()
                logging.error(error_text)
                last_line = error_text.strip().split('\n')[-1]
                self.log_message(f'{url} {self.tr("нет соединения")}: {last_line}')
        logging.info(f"Проверка ute_connect: {verified=}")
        return verified

    def ute_open(self, data):
        logging.debug(f"Got a signal: {data}")
        match = re.search(r'[A-Za-z]{6}', data["pair"])
        cleaned_pair = match.group(0) if match else None
        if cleaned_pair is None:
            logging.error(f"Пара {data['pair']} не поддерживается!")
            return
        data["pair"] = cleaned_pair
        data["direct"] = data["direct"].replace("/", "")
        if hasattr(self, 'bot'):
            if self.bot.is_connected is True:
                try:
                    logging.debug(data)
                    if self.bot is not None:
                        self.bot.mt4_signal(mt4_data=data)
                except Exception:
                    logging.exception("Exception occurred")
            else:
                logging.error("Client not connected! Reconnection...")
                self.bot.reconnect()
                self.ute_open(data)

    def connect_to_server(self):
        if self.flask_running is False:
            flask_thread.data_received.connect(self.ute_open)
            flask_thread.start()
            self.flask_running = True

    def start_client_thread(self):
        try:
            if self.allowToRunBot is False:
                QMessageBox.warning(self, self.tr("Внимание"), self.tr("Необходимо настроить мани-менеджмент перед подключением к платформе."))
                return

            if self.is_connected is False:
                if self.check_field_complete():
                    logging.info('Fields complete')
                    # Замена метода авторизации на проверку кодов
                    verified1 = self.ute_connect()
                    verified2, verify_text = check_aff(self.userid_edit.text().strip())
                    if 'error' in verify_text:
                        logging.warning(self.tr('Отказано. Нет соединения с платформой.'))
                        self.log_message('Отказано. Нет соединения с платформой.')
                        return
                    elif 'expired' in verify_text:
                        logging.warning(
                            self.tr(
                                'Тестовый период окончен, за дополнительной информацией обратитесь в telegram') + ' <a href="https://t.me/shulgin_gennadiy">https://t.me/shulgin_gennadiy</a>')
                        self.log_message(
                            self.tr(
                                'Тестовый период окончен, за дополнительной информацией обратитесь в telegram') + ' <a style="color: lightblue;" href="https://t.me/shulgin_gennadiy">https://t.me/shulgin_gennadiy</a>')
                        return
                    if verified1 or verified2:
                        auth_data = {
                            "selected_type_account": self.type_account.currentData(),
                            "token": self.token_edit.text().strip(),
                            "user_id": self.userid_edit.text().strip(),
                            "url": self.urlEdit.text().strip(),
                            "mt4_url": self.mt4Url.text().strip()
                        }
                        self.account_type = self.type_account.currentData()
                        save_auth_data(auth_data)

                        # Разрешаем торговлю
                        self.trading_paused = False

                        if self.bot:
                            self.connect_to_server()
                        self.is_connected = True

                        self.startButton.setEnabled(False)
                        self.change_widget_opacity(self.startButton, 50)

                        self.stopButton.setEnabled(True)
                        self.change_widget_opacity(self.stopButton, 100)

                        # self.log_message('Данные последней успешной авторизации сохранены.')

                    else:
                        logging.warning('Отказано. Вы не имеете доступ!')
                        self.log_message(self.tr('Отказано. Вы не имеете доступ!'))
                else:
                    logging.warning('Field (USerId or Token or url) don\'t complete4')
                    self.log_message(self.tr('Отказано. Заполните поля UserId и Token и url!'))
            else:
                # Если уже бот запущен
                self.trading_paused = False
                logging.info('Торговля возобновлена.')
                self.log_message(self.tr('Торговля возобновлена.'))

                self.startButton.setEnabled(False)
                self.change_widget_opacity(self.startButton, 50)

                self.stopButton.setEnabled(True)
                self.change_widget_opacity(self.stopButton, 100)

        except Exception as e:
            logging.exception(e)

    def change_widget_opacity(self, widget, opacity: int):
        opacity_value = max(0, min(opacity, 100)) / 100.0
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(opacity_value)
        widget.setGraphicsEffect(effect)

    def stop_client_thread(self):

        logging.info('Остановка торговли...')

        if self.bot:
            self.bot.close_connection()
        self.bot = None
        self.is_connected = False

        # Очистка серий
        if self.bot:
            self.bot.clean_counters()

        # Запрещаем торговлю
        self.trading_paused = True

        self.startButton.setEnabled(True)
        self.change_widget_opacity(self.startButton, 100)

        self.stopButton.setEnabled(False)
        self.change_widget_opacity(self.stopButton, 50)

        self.log_message(self.tr('Торговля приостановлена.'))

    def log_message(self, message):
        # Получаем текущее время в часовом поясе UTC+3
        current_time = datetime.now(pytz.utc)
        current_time = current_time.astimezone(pytz.timezone('Etc/GMT-3'))
        self.textBrowser.append(
            f"<p><span style='color:gray'>{current_time.strftime('%Y-%m-%d, %H:%M:%S')}:</span> {message}</p>")  # Зачем был ноль в конце?

    # В методе closeEvent
    def closeEvent(self, a0):
        # Проверим, есть ли активный бот
        if self.bot:

            if hasattr(self.bot, 'thread') and self.bot.thread.is_alive():
                # Завершаем поток
                self.bot.stop_event.set()  # Останавливаем поток ping_serv
                self.bot.thread.join(timeout=1)  # Ждем не более 1 секунды для завершения
                if self.bot.thread.is_alive():
                    self.bot.thread.terminate()  # Принудительно завершаем поток, если он все еще жив

            self.bot.close_connection()

        # Если Flask сервер все еще работает, принудительно завершаем его поток
        if flask_thread.isRunning():
            flask_thread.terminate()
            flask_thread.wait(300)  # Ждем не более 1 секунды для завершения
            if flask_thread.isRunning():
                os.kill(os.getpid(), signal.SIGTERM)  # Принудительно завершаем процесс, если поток не завершился

        # Останавливаем обновление новостей
        if hasattr(self, 'news_updater'):
            self.news_updater.stop()

        a0.accept()  # Разрешаем закрытие окна

    def on_datetime_changed(self, datetime):
        """ Обработчик изменения даты """
        logging.debug(f"Выбранная дата: {datetime.toString('dd.MM.yyyy HH:mm')}")  # Вывод в консоль

    def check_field_complete(self) -> object:
        token = self.token_edit.text()
        user_id = self.userid_edit.text()
        url = self.urlEdit.text()
        if token != '' and user_id != '' and (url != ''):
            logging.info('Field valid')
            return True
        return False

    # Статистика
    def update_all_statistic(self):
        try:
            data = load_statistic_data()
            trades = data.get("trades", [])

            """ Фильтр записей """
            # Получение тип счёта (сокращенное на английском)
            account_type = self.type_account_statistic.currentData()
            if account_type != 'any':
                # Фильтруем
                trades = list(filter(lambda deal: deal["type_account"] == account_type, trades))

            # Получение дат
            from_datetime = self.dateTimeEdit_1.dateTime()
            to_datetime = self.dateTimeEdit_2.dateTime()

            trades = list(filter(
                lambda deal: from_datetime <= datetime.strptime(deal["open_time"], "%d-%m-%Y %H:%M:%S") and (
                        deal["close_time"] == "⌛" or to_datetime >= datetime.strptime(deal["close_time"],
                                                                                      "%d-%m-%Y %H:%M:%S")),
                trades))

            self.trades_table.setRowCount(len(trades))  # Устанавливаем кол-во строк

            green_color = "rgb(40,167,69)"
            red_color = "rgb(168,62,62)"
            gray_color = "rgb(147,147,147)"

            trade_label = ["type_account", "asset", "open_time", "expiration", "close_time",
                           "open_price", "trade_type", "close_price", "points",
                           "volume", "percentage", "result"]

            header = self.trades_table.horizontalHeader()

            self.trades_table.setColumnWidth(0, 40)

            for row, trade in enumerate(trades[::-1]):
                for col, key in enumerate(trade_label):
                    value = str(trade.get(key, "N/A"))

                    if key == 'points' and value not in ["⌛", "N/A"]:
                        value = f"{-float(value):.10f}".rstrip('0').rstrip('.')

                    item = QLineEdit()
                    if col == 0:
                        item.setText(self.ACCOUNT_LABELS[value])
                        # for russ_key, val in TYPE_ACCOUNT.items():
                        #    if val == value:
                        #        item.setText(russ_key)
                    else:
                        item.setText(value)
                    item.setDisabled(True)
                    item.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    # Красим последний столбец
                    if col == 11:
                        if trade["open_price"] == "⌛":
                            item.setStyleSheet(f"background-color: {gray_color};border-radius: 0px; color: white;")
                        elif float(trade["open_price"]) == float(trade["close_price"]):
                            item.setStyleSheet(f"background-color: {gray_color};border-radius: 0px; color: white;")
                        elif value.startswith("-"):
                            item.setStyleSheet(f"background-color: {red_color};border-radius: 0px; color: white;")
                        else:
                            item.setStyleSheet(f"background-color: {green_color};border-radius: 0px; color: white;")
                    elif col == 6:
                        if value == "SELL":
                            item.setStyleSheet(
                                f"background-color: {allowed_color(self.theme)};border-radius: 0px; color: {red_color};font-weight: bold;")
                        elif value == "BUY":
                            item.setStyleSheet(
                                f"background-color: {allowed_color(self.theme)};border-radius: 0px; color: {green_color};font-weight: bold;")
                        elif float(trade["open_price"]) == float(trade["close_price"]):
                            item.setStyleSheet(
                                f"background-color: {allowed_color(self.theme)};border-radius: 0px; color: white;font-weight: bold;")
                    else:
                        item.setStyleSheet(f"background-color: {allowed_color(self.theme)};border-radius: 0px;")

                    # Рассчитываем ширину текста
                    font_metrics = QFontMetrics(item.font())
                    text_width = font_metrics.horizontalAdvance(item.text())

                    # Устанавливаем ширину QLineEdit с учетом отступов
                    if col < 0:
                        if text_width + 20 < 100:
                            item.setMinimumWidth(100)  # +20 для отступов
                        else:
                            item.setMinimumWidth(text_width + 20)  # +20 для отступов
                        header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
                    else:
                        item.setMinimumWidth(90)
                        header.setSectionResizeMode(col, QHeaderView.Stretch)

                    self.trades_table.setCellWidget(row, col, item)

            # self.trades_table.resizeColumnsToContents()

            data["trades"] = trades

            updated_data = recalculate_summary(data)
            if updated_data:
                self.update_summary(updated_data.get("summary", {}))
        except Exception:
            logging.exception("Exception occurred")
            time.sleep(10)

    def delete_statistic(self):
        try:

            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle(self.tr("Подтверждение удаления"))
            msg_box.setText(self.tr("Вы уверены, что хотите удалить выбранную статистику?"))

            # Языкозависимые подписи
            if self.language == 'ru':
                yes_text = "Да"
                no_text = "Нет"
            else:
                yes_text = "Yes"
                no_text = "No"


            # Добавляем кастомные кнопки
            yes_button = msg_box.addButton(yes_text, QMessageBox.YesRole)
            no_button = msg_box.addButton(no_text, QMessageBox.NoRole)

            msg_box.exec_()

            if not msg_box.clickedButton() == yes_button:
                return

            '''# Подтверждение удаления
            confirm = QMessageBox.question(
                self,
                self.tr("Подтверждение удаления"),
                self.tr("Вы уверены, что хотите удалить выбранную статистику?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )'''

            data = load_statistic_data()
            all_trades = data.get("trades", [])

            # Получение типа счета
            account_type = self.type_account_statistic.currentData()
            if account_type != 'any':
                filtered_trades = list(filter(lambda deal: deal["type_account"] == account_type, all_trades))
            else:
                filtered_trades = all_trades.copy()

            # Получение дат
            from_datetime = self.dateTimeEdit_1.dateTime()
            to_datetime = self.dateTimeEdit_2.dateTime()

            # Применение фильтра по датам
            filtered_trades = list(filter(
                lambda deal: from_datetime <= datetime.strptime(deal["open_time"], "%d-%m-%Y %H:%M:%S") and (
                        deal["close_time"] == "⌛" or to_datetime >= datetime.strptime(deal["close_time"],
                                                                                      "%d-%m-%Y %H:%M:%S")),
                filtered_trades
            ))

            # Удаление отфильтрованных записей из оригинального списка
            remaining_trades = [deal for deal in all_trades if deal not in filtered_trades]

            # Обновление и сохранение
            data["trades"] = remaining_trades
            save_statistic_data(data)

            # Обновление таблицы и сводки
            self.update_all_statistic()

        except Exception:
            logging.exception("Exception occurred during statistic deletion")
            time.sleep(10)

    def update_summary(self, summary):
        """ Обновляет блок сводки статистики """
        summary_labels = [
            "total", "profit", "loss", "refund", "winrate", "net_profit",
            "gross_profit", "gross_loss", "avg_profit_trade", "avg_loss_trade",
            "max_consecutive_wins", "max_consecutive_losses"
        ]
        summary_text_labels = [
            self.tr('Всего (Total)'),
            self.tr('Прибыльных (Profit)'),
            self.tr('Убыточных (Loss)'),
            self.tr('С возвратом (Refund)'),
            self.tr('Процент побед % (Win rate %)'),
            self.tr('Общий результат (Total net profit)'),
            self.tr('Сумма прибыльных (Gross profit)'),
            self.tr('Сумма убыточных (Gross loss)'),
            self.tr('Средняя прибыльная (Average profit trade)'),
            self.tr('Средняя убыточная (Average loss trade)'),
            self.tr('Макс. непрерывных выигрышей (Max consecutive wins)'),
            self.tr('Макс. непрерывных проигрышей (Max consecutive losses)')]

        for i, key in enumerate(summary_labels):
            value = str(summary.get(key, "N/A"))
            self.summary_table.setItem(i, 0, QTableWidgetItem(summary_text_labels[i]))  # Вставляем заголовок в таблицу

            item = QTableWidgetItem(value)
            self.summary_table.setItem(i, 1, item)  # Вставляем данные в таблицу
            item = self.summary_table.item(i, 1)
            if item:
                # item.setFlags(QtCore.Qt.ItemIsEnabled)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        header = self.summary_table.horizontalHeader()

        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    # Мани-менеджмент

    def initManageTable(self):
        self.manage_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        header = self.manage_table.horizontalHeader()
        self.manage_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.manage_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        # Минимальная ширина всех колонок
        header.setMinimumSectionSize(120)
        # header.setSectionResizeMode(0, QHeaderView.ResizeToContents)

        # Stretch всем колонкам, но с учётом минимального размера

        header.setSectionResizeMode(QHeaderView.Stretch)


        # self.manage_table.setColumnWidth(0, 40)  # Можно убрать, если растягиваете все

        data = load_money_management_data()

        cnt = 2
        for key, item in data.items():
            try:
                if cnt >= len(data) + 1:
                    cnt = 0
                self.addRow(
                    invest_val=item["investment"],
                    expiration_val=item["expiration"],
                    mm_type_val=item["mm_type"],
                    profit_val=item["take_profit"],
                    stop_val=item["stop_loss"],
                    on_win=item.get("on_win", cnt),
                    on_loss=item.get("on_loss", cnt),
                    skip_check=True,
                    add_copy=False,
                    header=header
                )
                cnt += 1
            except Exception:
                logging.exception("Exception occurred")

    def addRow(self, *args, invest_val="100", expiration_val="00:01:00",
               mm_type_val=MM_MODES[1],
               profit_val="100000", stop_val="100", on_win=1,
               on_loss=1, result_val='WIN', skip_check=False, add_copy=False, header=None):


        def place_default():
            for col in range(1, self.manage_table.columnCount()):
                # if i in [MM_TABLE_FIELDS["Результат"]]:
                #    continue

                item = QLineEdit()
                item.setAlignment(Qt.AlignmentFlag.AlignCenter)

                if col == MM_TABLE_FIELDS["Инвестиция"]:
                    item.setValidator(self.investment_validator)
                    item.setText(invest_val)
                elif col == MM_TABLE_FIELDS["Экспирация"]:
                    item.setValidator(self.expiration_validator)
                    item.setText(expiration_val)
                elif col == MM_TABLE_FIELDS["Тейк профит"]:
                    item.setValidator(self.digit_validator)
                    item.setText(profit_val)
                elif col == MM_TABLE_FIELDS["Стоп лосс"]:
                    item.setValidator(self.digit_validator)
                    item.setText(stop_val)
                elif col == MM_TABLE_FIELDS["Тип ММ"]:
                    item.setValidator(self.type_mm)
                    item.setText(mm_type_val)
                    # Подключаем сигнал изменения ячейки к слоту
                    item.textChanged.connect(self.update_mm_table)
                elif col == MM_TABLE_FIELDS["WIN"]:
                    item.setValidator(self.digit_validator)
                    item.setText(str(on_win))
                elif col == MM_TABLE_FIELDS["LOSS"]:
                    item.setValidator(self.digit_validator)
                    item.setText(str(on_loss))
                else:
                    item.setValidator(self.digit_validator)
                item.setStyleSheet(allowed_cell(self.theme))
                item.setMinimumWidth(120)
                # if header:
                    # header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
                self.manage_table.setCellWidget(rowCount, col, item)

        def place_previous_copy():
            prev_row = rowCount - 1
            for col in range(1, self.manage_table.columnCount()):
                prev_widget = self.manage_table.cellWidget(prev_row, col)
                if isinstance(prev_widget, QLineEdit):

                    copied_text = prev_widget.text()
                else:
                    copied_text = ""

                new_widget = QLineEdit()
                new_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                new_widget.setText(copied_text)

                # Применить нужный валидатор
                if col == MM_TABLE_FIELDS["Инвестиция"]:
                    new_widget.setValidator(self.investment_validator)
                elif col == MM_TABLE_FIELDS["Экспирация"]:
                    new_widget.setValidator(self.expiration_validator)
                elif col == MM_TABLE_FIELDS["Тейк профит"]:
                    new_widget.setValidator(self.digit_validator)
                elif col == MM_TABLE_FIELDS["Стоп лосс"]:
                    new_widget.setValidator(self.digit_validator)
                elif col == MM_TABLE_FIELDS["Тип ММ"]:
                    new_widget.setValidator(self.type_mm)
                    new_widget.textChanged.connect(self.update_mm_table)
                elif col in (MM_TABLE_FIELDS["WIN"], MM_TABLE_FIELDS["LOSS"]):
                    new_widget.setValidator(self.digit_validator)
                else:
                    new_widget.setValidator(self.digit_validator)

                new_widget.setStyleSheet(allowed_cell(self.theme))
                new_widget.setMinimumWidth(120)
                if header:
                    header.setSectionResizeMode(col, QHeaderView.Stretch)
                self.manage_table.setCellWidget(rowCount, col, new_widget)

        try:
            rowCount = self.manage_table.rowCount()
            self.manage_table.insertRow(rowCount)

            cnt_item = QLineEdit()
            cnt_item.setText(str(rowCount + 1))
            # Автоматический номер строки

            cnt_item.setDisabled(True)
            cnt_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cnt_item.setStyleSheet(allowed_cell(self.theme))
            # cnt_item.setMaximumWidth(40)
            self.manage_table.setCellWidget(rowCount, 0, cnt_item)

            # Валидация инвестиции
            if rowCount > 0:
                prev_value = self.manage_table.cellWidget(0, MM_TABLE_FIELDS["Инвестиция"]).text()
                prev_type = "percent" if "%" in prev_value else "number"

                if self.investment_type is None:
                    self.investment_type = prev_type

                current_value = self.manage_table.item(rowCount, MM_TABLE_FIELDS["Инвестиция"])
                if current_value and (("%" in current_value.text() and self.investment_type == "number") or
                                      ("%" not in current_value.text() and self.investment_type == "percent")):
                    QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Тип инвестиции должен быть единообразным!"))
                    self.manage_table.removeRow(rowCount)
                    return

            if add_copy == 1 and rowCount != 0:
                # Если таблица не пуста, копируем последнюю строку
                place_previous_copy()
            else:
                # Установка пустых значений
                place_default()

            if not skip_check:
                self.haveUnsavedRows = True
                self.update_mm_table(MM_MODES[self.selected_mm_mode])

        except Exception:
            logging.exception("Exception occurred")
            time.sleep(10)

    def saveData(self, nide_notification=False):
        data = {}

        def time_to_seconds(time_str):
            """Переводит время в формате 'hh:mm:ss' в количество секунд."""
            # Разделяем строку по двоеточию
            hours, minutes, seconds = map(int, time_str.split(":"))

            # Переводим время в секунды
            total_seconds = (hours * 3600) + (minutes * 60) + seconds
            return total_seconds

        try:
            rowCount = self.manage_table.rowCount()
            for row in range(rowCount):
                data[row] = {}
                # Проверка инвестиции
                investment_item = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["Инвестиция"])
                if investment_item:
                    value = investment_item.text().strip()

                    # TODO Проверка на число
                    if row == 0:
                        self.investment_type = "percent" if "%" in value else "number"
                    else:
                        if ("%" in value and self.investment_type == "number") or (
                                "%" not in value and self.investment_type == "percent"):
                            QMessageBox.warning(self, self.tr("Ошибка"),
                                                self.tr(
                                                    f"Несовместимый тип инвестиции в строке") + f" {row + 1}. " + self.tr(
                                                    "Во всех строках применяется ли бо конечное число, либо % от баланса на аккаунте."))
                            return
                    data[row]["investment"] = value

                    if hasattr(self, "account_type") and self.account_type == 'real_dollar' and not (
                            0.1 <= float(value) <= 2000):
                        self.log_message(
                            f"{self.tr('Баланс сделки в строке')} {row + 1} (${float(value)}) {self.tr('не удовлетворяет условиям (мин $0.1, макс $2,000)')}")
                        return
                    elif hasattr(self, "account_type") and self.account_type == 'real_rub' and not (
                            20 <= float(value) <= 200000):
                        self.log_message(
                            f"{self.tr('Баланс сделки в строке')} {row + 1} (₽{float(value)}) {self.tr('не удовлетворяет условиям (мин ₽20, макс ₽200,000)')}")
                        return

                # Проверка экспирации
                expiration_item = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["Экспирация"])
                if expiration_item:
                    value = expiration_item.text().strip()
                    if ":" in value:  # Формат времени
                        try:
                            exp_time = QTime.fromString(value, "hh:mm:ss")
                            # Текущее время
                            seconds = time_to_seconds(value)
                            # logging.debug(seconds)

                            if not (exp_time.isValid() and 86100 >= seconds >= 60):
                                QMessageBox.warning(self, self.tr("Ошибка"),
                                                    f"{self.tr('Неверный формат или слишком короткий интервал экспирации в строке')} {row + 1}")
                                raise ValueError("Неверный формат или слишком короткий интервал")
                            data[row]["expiration"] = value
                        except ValueError:
                            logging.exception("Exception occurred")
                            return
                    elif value.isdigit():  # В минутах
                        if int(value) not in [1, 5, 15, 30, 60]:
                            QMessageBox.warning(self, self.tr("Ошибка"),
                                                f"{self.tr('Экспирация в формате числа должна быть одним из следующих значений: 1, 5, 15, 30, 60 Строка')} {row + 1}")
                            return
                        data[row]["expiration"] = value
                    else:  # Должно быть числом
                        QMessageBox.warning(self, self.tr("Ошибка"),
                                            f"{self.tr('Экспирация должна быть числом или временем в строке')} {row + 1}")
                        return

                # Проверка типа ММ
                mm_item = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["Тип ММ"])

                if mm_item and mm_item.text().strip() not in MM_MODES.values():
                    QMessageBox.warning(self, self.tr("Ошибка"),
                                        f"{self.tr('Некорректный режим обработки в строке')} {row + 1}")
                    return
                if mm_item:
                    mm_text = mm_item.text().strip()
                    data[row]["mm_type"] = mm_text

                    # Сохраняем выбранный тип ММ
                    for n, m_name in MM_MODES.items():
                        if m_name == mm_text:
                            self.selected_mm_mode = n
                            break

                    self.update_mm_table(mm_text)

                    if not nide_notification:
                        if rowCount <= 1 and mm_text in [MM_MODES[1], MM_MODES[2], MM_MODES[3], MM_MODES[4]]:
                            QMessageBox.warning(self, self.tr("Ошибка"),
                                                self.tr(
                                                    "Для выбранного вами режима необходимо настроить хотя бы 2 строки"))
                            return

                # Проверка "WIN"
                on_win_item = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["WIN"])
                if on_win_item and int(on_win_item.text().strip()) > rowCount:
                    QMessageBox.warning(self, self.tr("Ошибка"),
                                        f'Параметр WIN выходит за диапазон таблицы в строке {row + 1}')
                    return

                if on_win_item and row != 0 and int(on_win_item.text().strip()) == (row + 1):
                    QMessageBox.warning(self, self.tr("Ошибка"),
                                        f"{self.tr('Параметр WIN не должен указывать на текущую строку в строке')} {row + 1}")
                    return

                if on_win_item:
                    data[row]["on_win"] = int(on_win_item.text().strip())

                # Проверка "WIN"
                on_loss_item = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["LOSS"])
                if on_loss_item and int(on_loss_item.text().strip()) > rowCount:
                    QMessageBox.warning(self, self.tr("Ошибка"),
                                        f"{self.tr('Параметр LOSS выходит за диапазон таблицы в строке')} {row + 1}")
                    return

                if on_loss_item and row != 0 and int(on_loss_item.text().strip()) == (row + 1):
                    QMessageBox.warning(self, self.tr("Ошибка"),
                                        f"{self.tr('Параметр LOSS не должен указывать на текущую строку в строке')} {row + 1}")
                    return

                if on_loss_item:
                    data[row]["on_loss"] = int(on_loss_item.text().strip())

                # Проверка результата
                """result_item = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["Результат"])
                if row > 0:
                    if result_item and result_item.currentText().strip() not in ["WIN", "LOSS"]:
                        QMessageBox.warning(self, "Ошибка", f"Результат должен быть WIN или LOSS в строке {row + 1}")
                        return
                data[row]["result_type"] = result_item.currentText().strip()"""

                # Проверка Тейк профит и Стоп лосс
                for col in [MM_TABLE_FIELDS["Тейк профит"], MM_TABLE_FIELDS["Стоп лосс"]]:
                    value_item = self.manage_table.cellWidget(row, col)
                    if value_item:
                        try:
                            float(value_item.text().strip())
                        except ValueError:
                            QMessageBox.warning(self, self.tr("Ошибка"),
                                                f"{self.tr('Тейк профит и Стоп лосс должны быть числами в строке')} {row + 1}")
                            return
                data[row]["take_profit"] = self.manage_table.cellWidget(row,
                                                                        MM_TABLE_FIELDS["Тейк профит"]).text().strip()
                data[row]["stop_loss"] = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["Стоп лосс"]).text().strip()

            if not nide_notification:
                QMessageBox.information(self, self.tr("Успех"), self.tr("Данные сохранены успешно!"))
                self.allowToRunBot = True
            self.haveUnsavedRows = False
            save_money_management_data(data)
            if self.bot:
                self.bot.clean_counters()
        except Exception:
            logging.exception("Exception occurred")
            time.sleep(10)

    def deleteClicked(self):

        # Если в таблице есть строки
        if self.manage_table.rowCount() > 0:
            # Удаляем последнюю строку
            self.manage_table.removeRow(self.manage_table.rowCount() - 1)

        if self.manage_table.rowCount() > 0:
            combo = self.manage_table.cellWidget(self.manage_table.rowCount() - 1, MM_TABLE_FIELDS["WIN"])
            combo.setText("0")
            combo = self.manage_table.cellWidget(self.manage_table.rowCount() - 1, MM_TABLE_FIELDS["LOSS"])
            combo.setText("0")
        # Сохраняем данные после изменения

        # self.saveData(nide_notification=True)

    def update_mm_table(self, text):
        if not text:
            return

        # Обновляем все строки в столбце "Тип ММ"
        for row in range(self.manage_table.rowCount()):
            combo = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["Тип ММ"])
            combo.setText(str(text))

        # Определяем, следует ли отключать элементы в зависимости от режима
        disable_fields = text in [MM_MODES[0], MM_MODES[1]]

        for row in range(self.manage_table.rowCount()):
            for col in range(1, self.manage_table.columnCount()):
                widget = self.manage_table.cellWidget(row, col)

                if col in [MM_TABLE_FIELDS["WIN"], MM_TABLE_FIELDS["LOSS"]]:
                    widget.setDisabled(disable_fields)
                    if disable_fields:
                        widget.setStyleSheet(blocked_cell(self.theme))
                    else:
                        widget.setStyleSheet(allowed_cell(self.theme))
                else:
                    if row > 0:
                        widget.setDisabled(text == MM_MODES[0])
                        if text == MM_MODES[0]:
                            widget.setStyleSheet(blocked_cell(self.theme))
                        else:
                            widget.setStyleSheet(allowed_cell(self.theme))
        self.selected_mm_mode = int(text)

class TransparentText(QLabel):
    def __init__(self, text, parent, theme):
        super().__init__(text, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Прозрачный фон
        self.setStyleSheet(f"color: {transparent_text_color(theme)};")  # Полупрозрачный текст (белый, 150/255 прозрачности)
        self.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.adjustSize()  # Автоматический размер под текст
        self.move(50, 50)  # Позиция текста внутри окна

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 0))  # Полупрозрачный черный фон под текстом
        painter.drawRect(self.rect())  # Рисуем фон
        super().paintEvent(event)


def resource_path(relative_path):
    """Возвращает абсолютный путь к ресурсу, работает и в PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)



if __name__ == '__main__':
    # Убираем работу с БД
    # session = db_init()
    try:
        flask_thread = FlaskThread()
        telegram_thread = TelegramBotThread(chat_id=CHAT_ID)

        port = 80

        # QtCore.QDir.addSearchPath('', '/')

        app_qt = QApplication(sys.argv)
        translator = QTranslator()
        lang = load_language()
        if lang != 'ru':
            if translator.load(resource_path(f"translations_{lang}.qm")):
                app_qt.installTranslator(translator)
            else:
                print("Не удалось загрузить перевод")

        main_app = MainWindow(lang)
        main_app.show()
        logging.info('APP started!')
        sys.exit(app_qt.exec())
    except Exception:
        logging.exception("Exception occurred")
