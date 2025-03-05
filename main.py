# Decompiled with PyLingual (https://pylingual.io)rgb(18,26,61)
# Internal filename: main.py
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import json
import os
import re
import signal
import sys
import time
import traceback
from datetime import datetime

import requests
import telebot
from PyQt6 import uic
from PyQt6.QtCore import QThread, pyqtSignal, QTime, Qt, QRegularExpression, QDate
from PyQt6.QtGui import QIcon, QRegularExpressionValidator, QFontMetrics, QFont, QPainter, QColor
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QFileDialog, QHeaderView, QMessageBox, \
    QLineEdit, QComboBox, QLabel
from flask import Flask, request, abort

from loggingfile import logging
from mm_trading import OptionSeries
from mm_types import MM_MODES, TYPE_ACCOUNT
from programm_files import save_money_management_data, load_money_management_data, save_auth_data, \
    load_auth_data
from scrollbar_style import scrollbarstyle

API_TOKEN = '8029150425:AAEmxk26MP4ZSpsnA433znXbDs4rW0EcKJI'
CURRENT_VERSION = '1.0.0'  # Текущая версия бота
CHAT_ID = '-1002397524864'

# Инициализация бота с использованием pyTelegramBotAPI
bot = telebot.TeleBot(API_TOKEN)

app = Flask(__name__)

# Id для сверки
ALLOWED_PARTNER_IDS = ["111-116", "777-13269"]

sys.setrecursionlimit(2000)

MM_TABLE_FIELDS = {
    "Тип ММ": 1,
    "Инвестиция": 2,
    "Экспирация": 3,
    "Результат": 4,
    # "Фильтр выплат": 5,
    "Тейк профит": 5,
    "Стоп лосс": 6
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
        try:
            pinned_message = self.get_last_pinned_message()
            logging.debug(f"Pinned message: {pinned_message}")
            if not pinned_message:
                self.version_check_result.emit(
                    {"status": False, "message": "Не удалось проверить актуальность версии."})
                return

            # Ищем версию в тексте закрепленного сообщения
            version_pattern = r"#(\d+\.\d+\.\d+)"
            match = re.search(version_pattern, pinned_message.text)

            if match:
                pinned_version = match.group(1)
                logging.debug(f"{pinned_version=} {CURRENT_VERSION=}")
                if pinned_version > CURRENT_VERSION:
                    self.version_check_result.emit(
                        {"status": False,
                         "message": "Внимание! Ваш бот устарел. Пожалуйста, обновите до последней версии (текущая "
                                    f"версия: {CURRENT_VERSION})."})

                else:
                    self.version_check_result.emit(
                        {"status": True, "message": "Вы используете актуальную версию бота."})
            else:
                self.version_check_result.emit(
                    {"status": False, "message": "Не удалось найти информацию о версии в закрепленном сообщении."})
        except Exception:
            traceback.print_exc()

    def run(self):
        self.check_version()


def check_aff(aff_id):
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

        # Сохраняем текущий ID проекта и chat_id пользователя
        data = {
            'user_id': user_id,
            'aff_id': aff_id
        }
        # Отправляем POST-запрос
        response = requests.post(url, json=data)

        # Проверяем статус-код ответа
        if response.status_code == 200:
            # Обрабатываем ответ
            response_data = response.json()  # Предполагая, что ответ в формате JSON
            if response_data['message'] == 8:
                return True
                # user_status = 8
                # user_b_dollar = float(response_data['money_dollar'])
                # user_b_rub = float(response_data['money_rub'])
            else:
                return False
        return False

    url_id_pairs = [["777-13269", "http://ute.limited/ajax/check_aff_trade_id.php"],
                    ["777-116", "http://ute.limited/ajax/check_aff_id.php"]]

    rezs = []
    for own_id, url in url_id_pairs:
        rezs.append(check(url, aff_id, own_id))

    if rezs[0] or rezs[1]:
        return True
    return False


class FlaskThread(QThread):
    data_received = pyqtSignal(dict)

    def run(self):
        try:
            auth_data = load_auth_data()
            if auth_data.get("mt4_url"):
                splitted_auth_data = auth_data.get("mt4_url").strip().replace("https://", "").replace("http://", "").split(
                    ':')
                if len(splitted_auth_data) == 2:
                    host, port = splitted_auth_data
                    port = int(port)
                else:
                    host = splitted_auth_data[0]
                    port = 80
            else:
                auth_data["mt4_url"] = "http://127.0.0.1:80"
                save_auth_data(auth_data)
                host = "127.0.0.1"
                port = 80
        except Exception:
            traceback.print_exc()
        print(host, port)
        app.run(host=host, port=port, use_reloader=False, debug=False)

    def send_data_to_qt(self, data):
        self.data_received.emit(data)


@app.route('/', methods=['GET'])
def query_example():
    pair = request.args.get('pair')
    direct = request.args.get('direct')
    if pair is None or direct is None:
        return abort(400, 'Record not found')
    flask_thread.send_data_to_qt({'pair': pair, 'direct': direct})
    return f'{pair}:{direct}'


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        if getattr(sys, 'frozen', False):
            applicationPath = sys._MEIPASS
        elif __file__:
            applicationPath = os.path.dirname(__file__)
        ui_path = os.path.join(applicationPath, 'inteface.ui')
        uic.loadUi(ui_path, self)
        icon_path = os.path.join(applicationPath, 'icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle('UTE Connect')

        self.pushButton.clicked.connect(self.start_client_thread)
        self.bot = None
        self.client_socket = None
        self.is_connected = False
        self.last_recv = None

        # Режим ММ
        self.selected_mm_mode = 0

        # Статистика
        self.load_json_button.clicked.connect(self.load_statistics_from_json)  # Привязываем кнопку

        # Менеджмент
        # Подключаем кнопки к функциям
        self.investment_type = None  # Тип инвестиций (None, "number", "percent")

        self.addButton.clicked.connect(self.addRow)
        self.saveButton.clicked.connect(self.saveData)
        self.haveUnsavedRows = False
        self.allowToRunBot = False

        # Регулярное выражение для проверки инвестиции (разрешены цифры и знак %)
        self.investment_validator = QRegularExpressionValidator(QRegularExpression(r"^\d+(\.\d{1})$"))
        self.digit_validator = QRegularExpressionValidator(QRegularExpression(r"^\d+?$"))
        self.expiration_validator = QRegularExpressionValidator(QRegularExpression(r"^(\d{2}:\d{2}:\d{2}|\d+)$"))
        self.type_mm = QRegularExpressionValidator(QRegularExpression(r"\d{1}"))

        self.initManageTable()

        # Дата пикеры
        self.dateEdit_1.setDate(QDate.currentDate())  # Устанавливаем текущую дату
        self.dateEdit_1.dateChanged.connect(self.on_date_changed)  # Подключаем обработчик

        self.dateEdit_2.setDate(QDate.currentDate())  # Устанавливаем текущую дату
        self.dateEdit_2.dateChanged.connect(self.on_date_changed)  # Подключаем обработчик

        # Удаление последней
        self.deleteButton.clicked.connect(self.deleteClicked)
        self.deleteButton.setCursor(Qt.CursorShape.PointingHandCursor)

        # Проверка версии
        self.check_version()

        # Создание первой строки
        if not load_money_management_data():
            self.addRow()

        self.selected_type_account = None

        auth_data = load_auth_data()
        if auth_data:
            self.token_edit.setText(auth_data['token'])
            self.userid_edit.setText(auth_data['user_id'])
            self.urlEdit.setText(auth_data['url'])
            self.type_account.setCurrentText(auth_data['selected_type_account'])
            self.account_type = TYPE_ACCOUNT[auth_data["selected_type_account"]]
            self.mt4Url.setText(auth_data.get("mt4_url", "http://127.0.0.1"))
            # self.log_message('Данные последней успешной авторизации установлены.')

        # Сохранение таблицы, без уведомления, если успешно
        self.saveData(nide_notification=True)

        # Скроллинг
        self.trades_table.setStyleSheet(scrollbarstyle)
        self.manage_table.setStyleSheet(scrollbarstyle)
        self.textBrowser.setStyleSheet(scrollbarstyle)
        self.textBrowser_2.setStyleSheet(scrollbarstyle)

        self.setStatusBar(None)

        # Добавляем текст поверх всех виджетов
        self.overlay_text = TransparentText(f'Версия: {CURRENT_VERSION}', self)
        self.update_text_position()  # Устанавливаем позицию текста

        self.fix_table()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_text_position()  # Обновляем позицию текста при изменении размера окна

    def update_text_position(self):
        """Обновляет позицию текста внизу окна."""
        text_width = self.overlay_text.width()
        text_height = self.overlay_text.height()
        window_width = self.width()
        window_height = self.height()

        # Располагаем текст снизу, по центру
        x = 15
        y = window_height - text_height - 15  # Отступ в 10 пикселей от нижнего края
        self.overlay_text.move(x, y)

    def fix_table(self):
        # на windows 10 они отображаются не корректно
        self.manage_table.setStyleSheet(self.manage_table.styleSheet() + """
        QTableWidget {
                                background: rgb(12,17,47);
                                color: white;
                                border: none;
                                font-size: 14px;
                                }
            QHeaderView::section {
                background-color: rgb(18, 26, 61);
                color: white;
                font-weight: bold;
            }
        """)

        self.trades_table.setStyleSheet(self.trades_table.styleSheet() + """
        QTableWidget {
                                background: rgb(12,17,47);
                                color: white;
                                border: none;
                                font-size: 14px;
                                }
                    QHeaderView::section {
                        background-color: rgb(18, 26, 61);
                        color: white;
                        font-weight: bold;
                    }
                """)

        self.textBrowser.setStyleSheet(self.textBrowser.styleSheet() + """
                QTextBrowser {
                                background-color: rgb(18, 26, 61);
                                color: white;
                                border-radius: 5px;
                                padding: 5px;
                                font-size: 12px;
}
                    """)

        self.textBrowser_2.setStyleSheet(self.textBrowser_2.styleSheet() + """
                QTextBrowser {
                                background-color: rgb(18, 26, 61);
                                color: white;
                                border-radius: 5px;
                                padding-left: 10px;
                                padding-right: 5px;
                                padding-top: 5px;
                                padding-bottom: 5px;
                                font-size: 12px;
}
                    """)

    # Проверка версии
    def check_version(self):
        try:
            # Запускаем проверку в отдельном потоке
            telegram_thread.version_check_result.connect(self.show_warning)
            telegram_thread.start()
        except:
            traceback.print_exc()

    def show_warning(self, callback_dict):
        status, message = callback_dict["status"], callback_dict["message"]
        # Используем QMessageBox для отображения предупреждения
        if status is False:
            QMessageBox.critical(self, "Проверка версии", message, QMessageBox.StandardButton.Close)
            self.close()

    def ute_connect(self):
        token = self.token_edit.text()
        user_id = self.userid_edit.text()
        url = self.urlEdit.text()
        auth_data = {
            "selected_type_account": self.type_account.currentText(),
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
                        self.log_message("Соединение установлено")
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
                self.log_message(f'{url} нет соединения: {last_line}')
        return verified

    def ute_open(self, data):
        logging.debug(data)
        match = re.search(r'[A-Za-z]{6}', data["pair"])
        cleaned_pair = match.group(0) if match else None
        if cleaned_pair is None:
            logging.error(f"Пара {data['pair']} не поддерживается!")
            return
        data["pair"] = cleaned_pair
        data["direct"] = data["direct"].replace("/", "")
        if self.bot.is_connected is True:
            try:
                logging.debug(data)
                if self.bot is not None:
                    self.bot.mt4_signal(mt4_data=data)
            except Exception:
                traceback.print_exc()
        else:
            logging.error("Client not connected! Reconnection...")
            self.bot.reconnect()
            self.ute_open(data)

    def connect_to_server(self):
        flask_thread.data_received.connect(self.ute_open)
        flask_thread.start()
        logging.info('Flask server running')
        # self.log_message('Server is running on http://127.0.0.1:80')

    def start_client_thread(self):
        if self.allowToRunBot is False:
            QMessageBox.warning(self, "Внимание", "Перед запуском, примените настройки.")
            return

        if self.is_connected is False:
            if self.check_field_complete():
                logging.info('Fields complete')
                # Замена метода авторизации на проверку кодов
                verified1 = self.ute_connect()
                verified2 = check_aff(self.userid_edit.text())
                if verified1 or verified2:
                    auth_data = {
                        "selected_type_account": self.type_account.currentText(),
                        "token": self.token_edit.text().strip(),
                        "user_id": self.userid_edit.text().strip(),
                        "url": self.urlEdit.text().strip(),
                        "mt4_url": self.mt4Url.text().strip()
                    }
                    self.account_type = TYPE_ACCOUNT[auth_data["selected_type_account"]]
                    save_auth_data(auth_data)

                    if self.bot:
                        self.connect_to_server()
                    self.is_connected = True
                    self.pushButton.setEnabled(False)
                    self.pushButton.setStyleSheet("""
                    QPushButton{
                        background-color: #192142;
                        border-radius: 0px; 
                        color: #8996c7;
                        border-radius: 5px;
                        padding: 8px;
                        font-size: 12px;
                    }
                    """)
                    # self.log_message('Данные последней успешной авторизации сохранены.')


                else:
                    logging.warning('Отказано. Вы не имеете доступ!')
                    self.log_message('Отказано. Вы не имеете доступ!')
            else:
                logging.warning('Field (USerId or Token or url) don\'t complete4')
                self.log_message('Отказано. Заполните поля UserId и Token и url!')
        else:  # inserted
            self.log_message('Остановка сервера...')
            logging.info('CLOSING server')
            if self.bot:
                self.bot.close_connection()
            self.bot = None
            self.pushButton.setText('Запустить')
            logging.info('SERVER close')
            self.is_connected = False
            self.log_message('Сервер остановлен')

    def log_message(self, message):
        self.textBrowser.append(
            f"<p><span style='color:gray'>{datetime.now().strftime('%Y-%m-%d, %H:%M:%S')}:</span> {message}</p>")  # Зачем был ноль в конце?

    # В методе closeEvent
    def closeEvent(self, a0):
        # Проверим, есть ли активный бот
        if self.bot:
            if self.bot.thread.is_alive():
                # Завершаем поток
                self.bot.stop_event.set()  # Останавливаем поток ping_serv
                self.bot.thread.join(timeout=1)  # Ждем не более 1 секунды для завершения
                if self.bot.thread.is_alive():
                    self.bot.thread.terminate()  # Принудительно завершаем поток, если он все еще жив

            self.bot.close_connection()

        # Если Flask сервер все еще работает, принудительно завершаем его поток
        if flask_thread.isRunning():
            flask_thread.terminate()
            flask_thread.wait(1000)  # Ждем не более 1 секунды для завершения
            if flask_thread.isRunning():
                os.kill(os.getpid(), signal.SIGTERM)  # Принудительно завершаем процесс, если поток не завершился

        a0.accept()  # Разрешаем закрытие окна

    def on_date_changed(self, date):
        """ Обработчик изменения даты """
        logging.debug(f"Выбранная дата: {date.toString('dd.MM.yyyy')}")  # Вывод в консоль

    def check_field_complete(self) -> object:
        token = self.token_edit.text()
        user_id = self.userid_edit.text()
        url = self.urlEdit.text()
        if token != '' and user_id != '' and (url != ''):
            logging.info('Field valid')
            return True
        return False

    # Статистика
    def load_statistics_from_json(self):
        """ Загружает данные из JSON-файла и обновляет UI """
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите JSON файл", "", "JSON Files (*.json)")
        if not file_path:
            return  # Если файл не выбран, выходим

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Обновление таблицы
        self.update_summary(data.get("summary", {}))
        self.update_table(data.get("trades", []))

        # Пример входных данных:

        # {
        #    "summary": {
        #        "total": 1236,
        #        "profit": 653,
        #        "loss": 123,
        #        "refund": 0,
        #        "net_profit": 300,
        #        "gross_profit": 3333,
        #        "gross_loss": 1111,
        #        "avg_profit_trade": 36,
        #        "avg_loss_trade": 23,
        #        "max_consecutive_wins": 3,
        #        "max_consecutive_losses": 3
        #    },
        #    "trades": [
        #        {
        #            "asset": "EURUSD",
        #            "open_time": "17-01-2025 6:40:23",
        #            "expiration": "0:01:00",
        #            "close_time": "17-01-2025 6:41:23",
        #            "open_price": 0.12555,
        #            "trade_type": "SELL",
        #            "close_price": 0.12547,
        #            "points": -0.24,
        #            "volume": 56,
        #            "refund": 0,
        #            "percentage": 82,
        #            "result": 3
        #        }
        #    ]
        # }

    def update_summary(self, summary):
        """ Обновляет блок сводки статистики """
        summary_labels = [
            "total", "profit", "loss", "refund", "net_profit",
            "gross_profit", "gross_loss", "avg_profit_trade", "avg_loss_trade",
            "max_consecutive_wins", "max_consecutive_losses"
        ]
        summary_text_labels = [label.strip() for label in """
            Всего (Total)
            Прибыльных (Profit)
            Убыточных (Loss)
            С возвратом (Refund)    
            Общий результат (Total net profit)   
            Сумма прибыльных (Gross profit)     
            Сумма убыточных (Gross loss)   
            Средняя прибыльная (Average profit trade) 
            Средняя убыточная (Average loss trade)         
            Макс. непрерывных выигрышей (Max consecutive wins)  
            Макс. непрерывных проигрышей (Max consecutive losses)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
           """.split('\n') if label.strip()]

        for i, key in enumerate(summary_labels):
            value = str(summary.get(key, "N/A"))
            self.summary_table.setItem(i, 0, QTableWidgetItem(summary_text_labels[i]))  # Вставляем заголовок в таблицу

            item = QTableWidgetItem(value)
            self.summary_table.setItem(i, 1, item)  # Вставляем данные в таблицу
            item = self.summary_table.item(i, 1)
            if item:
                # item.setFlags(QtCore.Qt.ItemIsEnabled)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def update_table(self, trades):
        """ Обновляет таблицу сделок """
        self.trades_table.setRowCount(len(trades))  # Устанавливаем кол-во строк

        trade_label = ["asset", "open_time", "expiration", "close_time",
                       "open_price", "trade_type", "close_price", "points",
                       "volume", "refund", "percentage", "result"]

        header = self.trades_table.horizontalHeader()

        self.trades_table.setColumnWidth(0, 40)
        try:
            for row, trade in enumerate(trades):
                for col, key in enumerate(trade_label):
                    value = str(trade.get(key, "N/A"))

                    item = QLineEdit()
                    item.setText(value)
                    item.setDisabled(True)
                    item.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    # Красим последний столбец
                    if col == 11:
                        if value.startswith("-"):
                            item.setStyleSheet("background-color: #11173b;border-radius: 0px; color: rgb(244,50,49);")
                        else:
                            item.setStyleSheet("background-color: #11173b;border-radius: 0px; color: rgb(0,215,49);")
                    else:
                        item.setStyleSheet("background-color: #11173b;border-radius: 0px;")

                    # Рассчитываем ширину текста
                    font_metrics = QFontMetrics(item.font())
                    text_width = font_metrics.horizontalAdvance(item.text())

                    # Устанавливаем ширину QLineEdit с учетом отступов
                    if col < 7:
                        if text_width + 20 < 100:
                            item.setMinimumWidth(100)  # +20 для отступов
                        else:
                            item.setMinimumWidth(text_width + 20)  # +20 для отступов
                        header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
                    else:
                        item.setMinimumWidth(90)
                        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

                    self.trades_table.setCellWidget(row, col, item)

                    # item = self.trades_table.item(row, col)
                    # if row % 2 == 0:
                    #     item.setBackground(QColor("#2b3661"))  # Светлее

            self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except Exception as e:
            traceback.print_exc()
            time.sleep(10)

    # Мани-менеджмент

    def initManageTable(self):
        # Устанавливаем растягивание всех колонок, кроме первой
        header = self.manage_table.horizontalHeader()

        # Устанавливаем фиксированную ширину для первого столбца
        self.manage_table.setColumnWidth(0, 40)  # Ширина первого столбца будет 100 пикселей

        # Растягиваем остальные столбцы
        for col in range(1, self.manage_table.columnCount()):
            if col in []:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
            else:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        data = load_money_management_data()

        for key, item in data.items():
            try:
                self.addRow(invest_val=item["investment"],
                            expiration_val=item["expiration"],
                            mm_type_val=item["mm_type"],
                            profit_val=item["take_profit"],
                            stop_val=item["stop_loss"],
                            result_val=item["result_type"], skip_check=True)
            except Exception as e:
                traceback.print_exc()

    def addRow(self, *args, invest_val="100", expiration_val="00:01:00",
               mm_type_val=MM_MODES[1],
               profit_val="100000", stop_val="100", result_val='WIN', skip_check=False):
        try:
            rowCount = self.manage_table.rowCount()
            self.manage_table.insertRow(rowCount)

            cnt_item = QLineEdit()
            cnt_item.setText(str(rowCount + 1))
            # Автоматический номер строки

            cnt_item.setDisabled(True)
            cnt_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cnt_item.setStyleSheet("background-color: #121a3d;border-radius: 0px;")
            cnt_item.setMaximumWidth(40)
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
                    QMessageBox.warning(self, "Ошибка", "Тип инвестиции должен быть единообразным!")
                    self.manage_table.removeRow(rowCount)
                    return

            # поле результат
            combo = QComboBox()
            if rowCount > 0 and self.selected_mm_mode != 1:
                combo.addItems(["WIN", "LOSS"])
                combo.setStyleSheet("""
                QComboBox {
                    background-color: #121a3d;border-radius: 0px;
                }
                QComboBox:on {
                    background-color: rgb(25, 34, 74);border-radius: 0px;
                }
                QComboBox::drop-down{
                    image: url(icons/arrow.ico);
                    width:12px;
                    margin-right: 8px;
                }
                QComboBox QListView {
                    background-color: rgb(25, 34, 74);
                    outline: 0px;
                    padding: 2px;
                    border-radius: 5px;
                    border: none;
                }
                QComboBox QListView:item {
                padding: 5px;
                border-radius: 3px;
                border-left: 2px solid rgb(18, 26, 61);
                }
                QComboBox QListView:item:hover {
                background: rgb(26,38,85);
                border-left: 2px solid rgb(33,62,118);
                }
                """)
            else:
                combo.addItems(["WIN", "LOSS"])
                combo.setDisabled(True)
                combo.setStyleSheet("""
                QComboBox {
                    background-color: #192142;border-radius: 0px; color: #8996c7;
                }
                QComboBox::drop-down{
                    image: url(icons/arrow.ico);
                    width:12px;
                    margin-right: 8px;
                }
                QComboBox QListView {
                    background-color: rgb(18, 26, 61);
                    outline: 0px;
                    padding: 2px;
                    border-radius: 5px;
                    border: none;
                }
                QComboBox QListView:item {
                padding: 5px;
                border-radius: 3px;
                border-left: 2px solid rgb(18, 26, 61);
                }
                QComboBox QListView:item:hover {
                background: rgb(26,38,85);
                border-left: 2px solid rgb(33,62,118);
                }
                """)
            combo.setCurrentText(result_val)
            self.manage_table.setCellWidget(rowCount, MM_TABLE_FIELDS["Результат"], combo)

            '''# поле мм
            combo_mm = QLineEdit()
            # combo_mm.setMinimumWidth(275)
            if rowCount > 0:
                # combo_mm.addItems([item for _, item in MM_MODES.items()])
                combo_mm.setStyleSheet("""
                QComboBox {
                    background-color: #121a3d;border-radius: 0px;
                }
                QComboBox:on {
                    background-color: rgb(25, 34, 74);border-radius: 0px;
                }
                QComboBox::drop-down{
                    image: url(icons/arrow.ico);
                    width:12px;
                    margin-right: 8px;
                }
                QComboBox QListView {
                    background-color: rgb(25, 34, 74);
                    outline: 0px;
                    padding: 2px;
                    border-radius: 5px;
                    border: none;
                }
                QComboBox QListView:item {
                padding: 5px;
                border-radius: 3px;
                border-left: 2px solid rgb(18, 26, 61);
                }
                QComboBox QListView:item:hover {
                background: rgb(26,38,85);
                border-left: 2px solid rgb(33,62,118);
                }
                """)
            else:
                combo_mm.addItems([item for _, item in MM_MODES.items()])
                combo_mm.setDisabled(True)
                combo_mm.setStyleSheet("""
                QComboBox {
                    background-color: #192142;border-radius: 0px; color: #8996c7;
                }
                QComboBox::drop-down{
                    image: url(icons/arrow.ico);
                    width:12px;
                    margin-right: 8px;
                }
                QComboBox QListView {
                    background-color: rgb(18, 26, 61);
                    outline: 0px;
                    padding: 2px;
                    border-radius: 5px;
                    border: none;
                }
                QComboBox QListView:item {
                padding: 5px;
                border-radius: 3px;
                border-left: 2px solid rgb(18, 26, 61);
                }
                QComboBox QListView:item:hover {
                background: rgb(26,38,85);
                border-left: 2px solid rgb(33,62,118);
                }
                """)
            combo_mm.setCurrentText(mm_type_val)
            self.manage_table.setCellWidget(rowCount, MM_TABLE_FIELDS["Тип ММ"], combo_mm)'''

            # Установка пустых значений
            for i in range(1, 7):
                if i in [MM_TABLE_FIELDS["Результат"]]:
                    continue

                item = QLineEdit()
                item.setAlignment(Qt.AlignmentFlag.AlignCenter)

                if i == MM_TABLE_FIELDS["Инвестиция"]:
                    item.setValidator(self.investment_validator)
                    item.setText(invest_val)
                elif i == MM_TABLE_FIELDS["Экспирация"]:
                    item.setValidator(self.expiration_validator)
                    item.setText(expiration_val)
                elif i == MM_TABLE_FIELDS["Тейк профит"]:
                    item.setValidator(self.digit_validator)
                    item.setText(profit_val)
                elif i == MM_TABLE_FIELDS["Стоп лосс"]:
                    item.setValidator(self.digit_validator)
                    item.setText(stop_val)
                elif i == MM_TABLE_FIELDS["Тип ММ"]:
                    item.setValidator(self.type_mm)
                    item.setText(mm_type_val)
                    # Подключаем сигнал изменения ячейки к слоту
                    item.textChanged.connect(self.update_mm_table)
                else:
                    item.setValidator(self.digit_validator)
                item.setStyleSheet("background-color: #121a3d;border-radius: 0px;")
                self.manage_table.setCellWidget(rowCount, i, item)

                # item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Дейстие
            # deleteButton = QPushButton("Удалить")
            # self.deleteButton.clicked.connect(self.deleteClicked)
            # self.deleteButton.setCursor(Qt.CursorShape.PointingHandCursor)
            # item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            if not skip_check:
                self.haveUnsavedRows = True
        except Exception:
            traceback.print_exc()
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
                            QMessageBox.warning(self, "Ошибка",
                                                f"Несовместимый тип инвестиции в строке {row + 1}. Во всех строках применяется ли бо конечное число, либо % от баланса на аккаунте.")
                            return
                    data[row]["investment"] = value

                    if hasattr(self, "account_type") and self.account_type == 'real_dollar' and not (
                            0.1 <= float(value) <= 2000):
                        self.log_message(
                            f"Баланс сделки в строке {row + 1} (${float(value)}) не удовлетворяет условиям (мин $0.1 "
                            f"макс $2,000)")
                        return
                    elif hasattr(self, "account_type") and self.account_type == 'real_rub' and not (
                            20 <= float(value) <= 200000):
                        self.log_message(
                            f"Баланс сделки в строке {row + 1} (₽{float(value)}) не удовлетворяет условиям (мин ₽20 "
                            f"макс ₽200,000)")
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
                                QMessageBox.warning(self, "Ошибка",
                                                    f"Неверный формат или слишком короткий интервал экспирации в "
                                                    f"строке {row + 1}")
                                raise ValueError("Неверный формат или слишком короткий интервал")
                            data[row]["expiration"] = value
                        except ValueError:
                            traceback.print_exc()
                            return
                    elif value.isdigit():  # В минутах
                        if int(value) not in [1, 5, 15, 30, 60]:
                            QMessageBox.warning(self, "Ошибка",
                                                f"Экспирация в формате числа должна быть одним из следующих значений: 1, 5, 15, 30, 60 Строка {row + 1}")
                            return
                        data[row]["expiration"] = value
                    else:  # Должно быть числом
                        QMessageBox.warning(self, "Ошибка",
                                            f"Экспирация должна быть числом или временем в строке {row + 1}")
                        return

                # Проверка типа ММ
                mm_item = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["Тип ММ"])

                if mm_item and mm_item.text().strip() not in MM_MODES.values():
                    QMessageBox.warning(self, "Ошибка", f"Некорректный режим обработки в строке {row + 1}")
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
                            QMessageBox.warning(self, "Ошибка",
                                                f"Для выбранного вами режима необходимо настроить хотя бы 2 строки")
                            return

                # Проверка результата
                if row > 0:
                    result_item = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["Результат"])
                    if result_item and result_item.currentText().strip() not in ["WIN", "LOSS"]:
                        QMessageBox.warning(self, "Ошибка", f"Результат должен быть WIN или LOSS в строке {row + 1}")
                        return
                data[row]["result_type"] = self.manage_table.cellWidget(row, MM_TABLE_FIELDS[
                    "Результат"]).currentText().strip()

                # Проверка Тейк профит и Стоп лосс
                for col in [MM_TABLE_FIELDS["Тейк профит"], MM_TABLE_FIELDS["Стоп лосс"]]:
                    value_item = self.manage_table.cellWidget(row, col)
                    if value_item:
                        try:
                            float(value_item.text().strip())
                        except ValueError:
                            QMessageBox.warning(self, "Ошибка",
                                                f"Тейк профит и Стоп лосс должны быть числами в строке {row + 1}")
                            return
                data[row]["take_profit"] = self.manage_table.cellWidget(row,
                                                                        MM_TABLE_FIELDS["Тейк профит"]).text().strip()
                data[row]["stop_loss"] = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["Стоп лосс"]).text().strip()

            if not nide_notification:
                QMessageBox.information(self, "Успех", "Данные сохранены успешно!")
                self.allowToRunBot = True
            self.haveUnsavedRows = False
            save_money_management_data(data)
            if self.bot:
                self.bot.clean_counters()
        except Exception:
            traceback.print_exc()
            time.sleep(10)

    def deleteClicked(self):
        # Получаем количество строк в таблице
        row_count = self.manage_table.rowCount()

        # Если в таблице есть строки
        if row_count > 0:
            # Удаляем последнюю строку
            self.manage_table.removeRow(row_count - 1)

        # Сохраняем данные после изменения
        self.saveData(nide_notification=True)

    def update_mm_table(self, text):
        # Когда значение в одном из комбобоксов изменится, обновляем все строки в этом столбце
        for row in range(self.manage_table.rowCount()):
            combo = self.manage_table.cellWidget(row, MM_TABLE_FIELDS["Тип ММ"])  # Получаем QComboBox из ячейки
            combo.setText(text)  # Устанавливаем тот же текст во всех строках

            # При режиме 4, отключаем поле Результат и другие

            for row in range(1, self.manage_table.rowCount()):

                for i in range(1, 7):
                    if i in [MM_TABLE_FIELDS["Результат"]] and text in [MM_MODES[1], MM_MODES[0]]:
                        combo_result = self.manage_table.cellWidget(row, i)  # Получаем QComboBox из ячейки
                        combo_result.setDisabled(True)
                        combo_result.setStyleSheet("""
                                            QComboBox {
                                                background-color: #192142;border-radius: 0px; color: #8996c7;
                                            }
                                            QComboBox::drop-down{
                                                image: url(icons/arrow.ico);
                                                width:12px;
                                                margin-right: 8px;
                                            }
                                            QComboBox QListView {
                                                background-color: rgb(18, 26, 61);
                                                outline: 0px;
                                                padding: 2px;
                                                border-radius: 5px;
                                                border: none;
                                            }
                                            QComboBox QListView:item {
                                            padding: 5px;
                                            border-radius: 3px;
                                            border-left: 2px solid rgb(18, 26, 61);
                                            }
                                            QComboBox QListView:item:hover {
                                            background: rgb(26,38,85);
                                            border-left: 2px solid rgb(33,62,118);
                                            }
                                            """)

                    elif i not in [MM_TABLE_FIELDS["Результат"]] and text in MM_MODES[0]:
                        line_edit_element = self.manage_table.cellWidget(row, i)

                        line_edit_element.setDisabled(True)
                        line_edit_element.setStyleSheet("""
                        QLineEdit {
                            background-color: #192142;border-radius: 0px; color: #8996c7;
                        }
                        """)

                for i in range(1, 7):
                    if i in [MM_TABLE_FIELDS["Результат"]] and text not in [MM_MODES[1], MM_MODES[0]]:
                        combo_result = self.manage_table.cellWidget(row, i)  # Получаем QComboBox из ячейки
                        combo_result.setDisabled(False)
                        combo_result.setStyleSheet("""
                                            QComboBox {
                                                background-color: #121a3d;border-radius: 0px;
                                            }
                                            QComboBox:on {
                                                background-color: rgb(25, 34, 74);border-radius: 0px;
                                            }
                                            QComboBox::drop-down{
                                                image: url(icons/arrow.ico);
                                                width:12px;
                                                margin-right: 8px;
                                            }
                                            QComboBox QListView {
                                                background-color: rgb(25, 34, 74);
                                                outline: 0px;
                                                padding: 2px;
                                                border-radius: 5px;
                                                border: none;
                                            }
                                            QComboBox QListView:item {
                                            padding: 5px;
                                            border-radius: 3px;
                                            border-left: 2px solid rgb(18, 26, 61);
                                            }
                                            QComboBox QListView:item:hover {
                                            background: rgb(26,38,85);
                                            border-left: 2px solid rgb(33,62,118);
                                            }
                                            """)

                    elif i not in [MM_TABLE_FIELDS["Результат"]] and text not in MM_MODES[0]:
                        line_edit_element = self.manage_table.cellWidget(row, i)

                        line_edit_element.setDisabled(False)
                        line_edit_element.setStyleSheet("""
                        QLineEdit {
                            background-color: #121a3d;border-radius: 0px;
                        }
                        """)


class TransparentText(QLabel):
    def __init__(self, text, parent):
        super().__init__(text, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Прозрачный фон
        self.setStyleSheet("color: rgba(255, 255, 255, 150);")  # Полупрозрачный текст (белый, 150/255 прозрачности)
        self.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.adjustSize()  # Автоматический размер под текст
        self.move(50, 50)  # Позиция текста внутри окна

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 30))  # Полупрозрачный черный фон под текстом
        painter.drawRect(self.rect())  # Рисуем фон
        super().paintEvent(event)


if __name__ == '__main__':
    # Убираем работу с БД
    # session = db_init()
    try:
        flask_thread = FlaskThread()
        telegram_thread = TelegramBotThread(chat_id=CHAT_ID)

        app_qt = QApplication(sys.argv)
        main_app = MainWindow()
        main_app.show()
        logging.info('APP started!')
        sys.exit(app_qt.exec())
    except Exception:
        traceback.print_exc()
