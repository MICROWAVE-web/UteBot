import ast
import json
import ssl
import threading
import time
import uuid
from datetime import timedelta, datetime

import pytz
from websocket import WebSocketApp, WebSocketConnectionClosedException

from loggingfile import logging
from mm_types import TYPE_ACCOUNT
from programm_files import load_money_management_data
from utils import (get_expiration, check_availability_time_range,
                   add_pending_option_to_statistic, convert_datetime_format,
                   update_option_in_statistic)


def exeptions_determniant(err):
    errs = {
        "Error 1": "The amount of investment entered exceeds the trade balance",
        "Error 2": "The investment amount entered exceeds the maximum allowed",
        "Error 3": "The selected asset is not available",
        "Error 4": "The investment amount entered is below the minimum",
        "Error 01": "The amount of investment entered exceeds the trade balance",
        "Error 02": "The investment amount entered exceeds the maximum allowed",
        "Error 03": "The selected asset is not available",
        "Error 04": "The investment amount entered is below the minimum",
        "Error 12": "It is prohibited to use a real account",
        "Error 20": "Invalid account type or number of open options exceeded",
        "Error 21": "The asset is currently unavailable!",
        "Error 32": "Incorrect expiration time"
    }
    return f"{err}: {errs[err]}"


class OptionSeries:
    def __init__(self, auth_data, window, url, userid, token):

        self.last_opened_options_data = []

        self.window = window
        self.account_type_russ = auth_data["selected_type_account"]
        self.account_type = TYPE_ACCOUNT[auth_data["selected_type_account"]]

        # UTE BOt init:
        self.url = f"{url}/?userId={userid}&token={token}"
        self.serv_answ = []
        self.ute_data = None
        self.stop_event = threading.Event()
        self.pending_requests = {}
        self.connection_established = threading.Event()

        self.is_connected = False

        # WebSocketApp initialization
        self.ws = WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_close=self.on_close,
            on_error=self.on_error
        )

        # Start WebSocket in a separate thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever,
                                          kwargs={'sslopt': {"cert_reqs": ssl.CERT_NONE}})
        self.ws_thread.daemon = True
        self.ws_thread.start()

        # Wait for initial connection setup
        if not self.connection_established.wait(timeout=4):
            raise ConnectionError("Connection timeout")

        # Start ping thread
        self.ping_thread = threading.Thread(target=self.ping_serv)
        self.ping_thread.daemon = True
        self.ping_thread.start()

        self.block_mt_pairs = set()

        self.COUNTERS = None
        self.MT4_SIGNALS = None
        self.clean_counters()

        self.pair_list = self.get_only_pair_list()

        self.deal_series = []

        self.update_mm_data()

    def clean_counters(self):
        self.COUNTERS = {
            "type_1": {},  # Храним пару -> индекс
            "type_2": {},
            # Храним пару -># Храним id текущих опционов: индекс в таблице, при переходе к слудющему, удаляем старый.
            "type_3": 0,
            # Храним пару -> # Храним id текущих опционов: индекс в таблице, при переходе к слудющему, удаляем старый.
            "type_4": {}  # Храним пару -> индекс
        }
        # Сохраненные mt4 сигналы
        self.MT4_SIGNALS = {
            "type_0": {},
            "type_1": {},
            "type_2": {},
            "type_3": {},
            "type_4": {},
        }

        # Очистка при смене режима
        self.block_mt_pairs = set()

    def update_mm_data(self):
        mm_data = load_money_management_data()
        self.deal_series = []
        for key, item in mm_data.items():
            self.deal_series.append(item)

        # Вывод списка ММ таблицы
        logging.debug(f"{self.deal_series}")

    def should_trade(self, pair):
        # Проверка дополнительных настроек
        additional_check, additional_reason, additional_message = self._should_trade(pair)
        if not additional_check:
            if additional_reason == "news":
                additional_reason = "Новостной фильтр"
            elif additional_reason == "wrong_pair":
                additional_reason = "Разрешенные валютные пары"
            elif additional_reason == "wrong_time":
                additional_reason = "Расписание"
            elif additional_reason == "pause":
                logging.info("Торговля запрещена - пауза!")
                return False

            text_message = f"Торговля запрещена настройками для {pair}: {additional_reason} {additional_message}"
            logging.warning(text_message)
            self.window.log_message(text_message)
            return False
        return True

    def _should_trade(self, pair):
        # Проверка новостного фильтра
        if self.window.trading_paused:
            return False, "pause", None

        news_check, target_news = self.window.isInNewsBlackout(pair)
        if news_check:
            return False, "news", target_news.get("event")
        # Проверка дополнительных параметров

        # Проверка разрешенных пар
        print(self.window.settings)

        if not self.window.settings["pairs"].get(pair, True):
            return False, "wrong_pair", None

        # Текущее время
        now = datetime.now(pytz.timezone('Etc/GMT-3'))
        current_time = now.time()
        current_day = now.strftime("%a")  # Формат: Mon, Tue...

        # Маппинг на русские дни
        day_mapping = {
            "Mon": "Пн",
            "Tue": "Вт",
            "Wed": "Ср",
            "Thu": "Чт",
            "Fri": "Пт",
            "Sat": "Сб",
            "Sun": "Вс"
        }

        current_day_ru = day_mapping.get(current_day)
        if not current_day_ru or current_day_ru not in self.window.settings["schedule"]:
            return False, "wrong_time", None

        day_settings = self.window.settings["schedule"][current_day_ru]

        # Проверка включен ли день
        if not day_settings["enabled"]:
            return False, "wrong_time", None

        # Проверка временных интервалов
        for interval in day_settings["intervals"]:
            start_time = datetime.strptime(interval["start"], "%H:%M").time()
            end_time = datetime.strptime(interval["end"], "%H:%M").time()

            if start_time <= current_time <= end_time:
                return True, "", None

        return False, "wrong_time", None

    def mt4_signal(self, mt4_data: dict):
        self.update_mm_data()
        # Данные из МТ4
        mt4_pair = mt4_data["pair"]
        mt4_direct = mt4_data['direct']

        # Проверка дополнительных настроек
        additional_check = self.should_trade(mt4_pair)
        if not additional_check:
            return

            # Провера типа ММ и наличия активных открытых опционов
        logging.debug(f"{self.block_mt_pairs=} {self.window.selected_mm_mode=}")
        if self.window.selected_mm_mode == 2 and mt4_pair in self.block_mt_pairs:
            text = f"{mt4_pair} сделка не открыта, есть открытый опцион по {mt4_pair}"
            self.window.log_message(text)
            logging.debug(text)
            return
        elif self.window.selected_mm_mode == 3 and len(self.block_mt_pairs) > 0:
            text = f"{mt4_pair} сделка не открыта, есть открытый опцион."
            self.window.log_message(text)
            logging.debug(text + f' {self.block_mt_pairs=}')
            return
        elif self.window.selected_mm_mode == 4 and mt4_pair in self.block_mt_pairs:
            text = f"{mt4_pair} сделка не открыта, есть открытый опцион по {mt4_pair}"
            self.window.log_message(text)
            logging.debug(text + f' {self.block_mt_pairs=}')
            return

        deal_index = 0

        # Увеличение счетчика для режима 1 для новой пары
        if self.window.selected_mm_mode == 1:
            self.MT4_SIGNALS["type_1"][mt4_pair] = [mt4_pair, mt4_direct]
            if not self.COUNTERS["type_1"].get(mt4_pair):
                self.COUNTERS["type_1"][mt4_pair] = 0
                deal_index = 0
            else:
                deal_index = self.COUNTERS["type_1"][mt4_pair]

            if deal_index >= len(self.deal_series):
                self.COUNTERS["type_1"][mt4_pair] = 0
                deal_index = 0

        # Инициализация новой серии по режиму 2 для пары
        elif self.window.selected_mm_mode == 2:
            self.MT4_SIGNALS["type_2"][mt4_pair] = [mt4_pair, mt4_direct]
            self.COUNTERS["type_2"][mt4_pair] = 0
            deal_index = 0

        # По новому сигналу любого актива
        elif self.window.selected_mm_mode == 3:
            self.MT4_SIGNALS["type_3"][mt4_pair] = [mt4_pair, mt4_direct]
            deal_index = self.COUNTERS["type_3"]

        # По новому сигналу одно актива (парралельно)
        elif self.window.selected_mm_mode == 4:
            self.MT4_SIGNALS["type_4"][mt4_pair] = [mt4_pair, mt4_direct]
            if not self.COUNTERS["type_4"].get(mt4_pair):
                self.COUNTERS["type_4"][mt4_pair] = 0
            else:
                deal_index = self.COUNTERS["type_4"][mt4_pair]

        elif self.window.selected_mm_mode == 0:
            self.MT4_SIGNALS["type_0"][mt4_pair] = [mt4_pair, mt4_direct]

        self.process_option(mt4_pair=mt4_pair, mt4_direct=mt4_direct, new_serial=True, counter=deal_index)

    def process_option(self, mt4_pair, mt4_direct, new_serial=False, counter=0, ):
        logging.debug(f"{self.deal_series=}")
        self.reconnect()

        # Проверка дополнительных настроек
        additional_check = self.should_trade(mt4_pair)
        if not additional_check:
            return

        # Получение текущей сделки
        current_deal = self.deal_series[counter]
        logging.debug(f"{current_deal=}")

        if new_serial:
            serial_start_points = []
            serial_time_long = timedelta()
            serial_start_points.append(serial_time_long)

            # Проверка на интервалы сниженной выплаты только для режима 2 всей серии наперед
            if self.window.selected_mm_mode == 2:
                for deal in self.deal_series:
                    expiration_data = get_expiration(deal)
                    serial_time_long += expiration_data["time_delta"]
                    serial_start_points.append(serial_time_long)

            # Проверка на интервалы сниженной выплаты только для режима 1, 3, 4 в момент текущей сделки
            elif self.window.selected_mm_mode in [0, 1, 3, 4]:
                expiration_data = get_expiration(current_deal)
                serial_time_long += expiration_data["time_delta"]
                serial_start_points.append(serial_time_long)

            chkup, reason = check_availability_time_range(serial_start_points)
            if not chkup and reason == "weekend":
                text = f"{'Серия опционов' if self.window.selected_mm_mode == 2 else 'Опцион'} пересекается " \
                       f"с выходных днём. " \
                       f" Открытие опциона ({mt4_pair}:{mt4_direct}) остановлено."
                self.window.log_message(text)
                logging.debug(text)

                return
            elif not chkup and reason == "low":
                text = f"{'Серия опционов' if self.window.selected_mm_mode == 2 else 'Опцион'} пересекается " \
                       f"с расписанием снижения выплат. " \
                       f"Открытие опциона ({mt4_pair}:{mt4_direct}) остановлено."
                self.window.log_message(text)
                logging.debug(text)
                return

        # Проверка стоп тейк
        take_profit = current_deal['take_profit']
        stop_loss = current_deal['stop_loss']
        account_balance = self.get_balance(account_type=self.account_type)

        logging.debug(f"{take_profit=}")
        logging.debug(f"{stop_loss=}")
        logging.debug(f"{account_balance=}")

        take_profit = float(take_profit)
        stop_loss = float(stop_loss)
        account_balance = float(account_balance)

        if account_balance >= take_profit:
            text = f"Баланс превысил <span style='color:green'>Тейк профит</span>. " \
                   f"Открытие опциона ({mt4_pair}:{mt4_direct}) остановлено."
            self.window.log_message(text)
            logging.debug(text)
            return
        elif account_balance <= stop_loss:

            text = f"Баланс меньше <span style='color:red'>Стоп лосс</span>. " \
                   f"Открытие опциона ({mt4_pair}:{mt4_direct}) остановлено."
            self.window.log_message(text)
            logging.debug(text)
            return

        # Проверка investment
        if "%" in current_deal["investment"]:
            investment = round(account_balance * float(current_deal["investment"].replace("%", "")) / 100.0, 1)
        else:
            investment = round(float(current_deal["investment"]), 1)

        # Проверка суммы сделки (Счёт доллар - мин 0.1 макс 2,000 \ Счёт рубль - мин 20 макс 200,000)
        logging.debug(f"{investment=}")
        if self.account_type == 'real_dollar' and not (0.1 <= investment <= 2000):
            self.window.log_message(
                f"Баланс сделки (${investment}) не удовлетворяет условиям для открытия "
                f"опциона ({mt4_pair}:{mt4_direct}) на аккаунте «{self.account_type_russ}». "
                f"(мин 0.1 макс 2,000)")
            return
        elif self.account_type == 'real_rub' and not (20 <= investment <= 200000):
            self.window.log_message(
                f"Баланс сделки (₽{investment}) не удовлетворяет условиям для открытия "
                f"опциона ({mt4_pair}:{mt4_direct}) на аккаунте «{self.account_type_russ}». "
                f"(мин 20 макс 200,000)")
            return

        # Обработка экспирации
        expiration_data = get_expiration(current_deal)
        deal_time = expiration_data["deal_time"]
        w_type_exp = expiration_data["w_type_exp"]

        self.pair_list = self.get_only_pair_list()
        logging.debug(f"{self.pair_list=}")
        self.window.log_message(f"Открытие опциона... ({mt4_pair}:{mt4_direct})")
        if mt4_pair in self.pair_list['pair_list']:

            percent = self.pair_list['pair_list'].get(mt4_pair)["percent"] if self.pair_list['pair_list'].get(
                mt4_pair) else 0

            # Создаем поток
            '''threading.Thread(
                target=self._open_option_async,
                args=(mt4_pair, mt4_direct, current_deal, deal_time, percent, w_type_exp),
                daemon=True
            ).start()'''

            response = self.open_option(pair_name=mt4_pair, up_dn=mt4_direct.lower(),
                                        sum_option=current_deal["investment"],
                                        type_account=self.account_type, time_h=deal_time[0],
                                        time_m=deal_time[1],
                                        time_s=deal_time[2], percent_par=percent, w_type_exp=w_type_exp)
            logging.debug(f"OPTION OPENED: {response}")

        else:
            text = f"Пары {mt4_pair} не существует"
            self.window.log_message(text)
            logging.warning(text)
            return

        if self.window.selected_mm_mode in [2, 3, 4]:
            # В скоре будет открыт опцион с режимом 2. В этом режиме запрещён прием сигналов по текущей валютной паре
            # до окончания текущей серии опционов
            self.block_mt_pairs.add(mt4_pair)

        # Уведомление
        self.window.log_message(
            f'Опцион открыт. Актив: {mt4_pair}, Направление: {mt4_direct}, '
            f'Инвестиция: {current_deal["investment"]}, '
            f'Экспирация: {current_deal["expiration"]}, Режим №{self.window.selected_mm_mode}, Строка {counter + 1}.'
            if "Deal open" in str(self.serv_answ[(-1)]) else str(self.serv_answ[(-1)]))
        logging.info('Option open')

        # Увеличение счётчиков
        if self.window.selected_mm_mode == 1:
            self.COUNTERS["type_1"][mt4_pair] += 1

        # Для режимов 2, 3, 4 используем колонки WIN и LOSS
        """elif self.window.selected_mm_mode == 2:
            self.COUNTERS["type_2"][mt4_pair] += 1
        elif self.window.selected_mm_mode == 3:
            self.COUNTERS["type_3"] += 1
        elif self.window.selected_mm_mode == 4:
            self.COUNTERS["type_4"][mt4_pair] += 1"""

        # ^^^ Увеличение счетчико происходит в option finished

    def _handle_pending_option_async(self, pair_name, up_dn, sum_option, time_h, time_m, time_s, percent_par):
        t1 = datetime.now()
        td = timedelta(seconds=3)

        while datetime.now() - t1 < td:
            if not self.last_opened_options_data:
                time.sleep(0.1)
                continue
            print(self.last_opened_options_data)
            option_data = self.last_opened_options_data.pop(-1)
            option_id = option_data.get("api_massive_option")
            if option_id:
                option_id = option_id[0].get("option_id")
            if option_id:
                pending_data = {
                    "type_account": self.account_type,
                    "asset": pair_name,
                    "open_time": datetime.now(pytz.timezone('Etc/GMT-3')).strftime("%d-%m-%Y %H:%M:%S"),
                    "expiration": f"{time_h}:{time_m}:{time_s}",
                    "close_time": "⌛",
                    "open_price": "⌛",
                    "trade_type": 'BUY' if up_dn == 'up' else 'SELL',
                    "close_price": "⌛",
                    "points": "⌛",
                    "volume": float(sum_option),
                    "refund": 0,
                    "percentage": f"{percent_par}%" if percent_par else "-",
                    "result": "⌛",
                    "loss_refund": False
                }
                add_pending_option_to_statistic(option_id, pending_data)

        self.window.btn_apply.click()

    def option_finished(self, option_data):

        option_result_word = option_data["info_finish_option"][0]["finish_current_result"].lower()

        # Если пришел возврат в 50%, считаем как убыточную сделку
        loss_refund = False
        if '-1' in option_result_word:
            option_result_word.replace("-1", "loss", 1)
            loss_refund = True

        # Извлекаем option_id
        option_id = option_data["info_finish_option"][0].get("option_id")
        if option_id:
            # Формируем реальные данные
            if self.account_type in ["real_dollar", "demo"]:
                money_symbol = "$"
            else:
                money_symbol = "₽"

            if loss_refund:
                real_result = float(option_data["info_finish_option"][0]["finish_current_result_sum"]) - float(
                    option_data["info_finish_option"][0]['sum'])
            else:
                real_result = float(option_data["info_finish_option"][0]['finish_current_result_sum'])

            real_data = {
                "close_time": convert_datetime_format(option_data["info_finish_option"][0]["time_close"]),
                "open_price": float(option_data["info_finish_option"][0]["price_open"]),
                "close_price": float(option_data["info_finish_option"][0]["close_price"]),
                "points": round(
                    float(option_data["info_finish_option"][0]["price_open"]) -
                    float(option_data["info_finish_option"][0]["close_price"]),
                    6
                ),
                "result": f"{real_result}{money_symbol}",
                "loss_refund": loss_refund
            }

            # Обновляем запись
            update_option_in_statistic(option_id, real_data)
            self.window.btn_apply.click()

        option_symbol = str(option_data["info_finish_option"][0]["symbol"])

        logging.debug(f"OPTION FINISHED: {option_data}")
        self.update_mm_data()

        if self.window.selected_mm_mode == 0 and self.MT4_SIGNALS["type_0"].get(option_symbol):
            mt4_pair, mt4_direct = self.MT4_SIGNALS["type_0"][option_symbol]

            # Сохраняем в статистику
            additional_data = {
                "percentage": self.pair_list['pair_list'].get(mt4_pair)["percent"] if self.pair_list['pair_list'].get(
                    mt4_pair) else "-",
                "account_type": self.account_type,
                "direction": mt4_direct,
                "option_result_word": option_result_word, "loss_refund": loss_refund
            }
            # add_option_to_statistic(option_data, additional_data)

            # Обновляем статистику
            self.window.btn_apply.click()

        elif self.window.selected_mm_mode == 1 and self.MT4_SIGNALS["type_1"].get(option_symbol):
            mt4_pair, mt4_direct = self.MT4_SIGNALS["type_1"][option_symbol]

            # Сохраняем в статистику
            additional_data = {
                "percentage": self.pair_list['pair_list'].get(mt4_pair)["percent"] if self.pair_list['pair_list'].get(
                    mt4_pair) else "-",
                "account_type": self.account_type,
                "direction": mt4_direct,
                "option_result_word": option_result_word, "loss_refund": loss_refund
            }
            # add_option_to_statistic(option_data, additional_data)

            # Обновляем статистику
            self.window.btn_apply.click()

        elif self.window.selected_mm_mode == 2 and self.MT4_SIGNALS["type_2"].get(option_symbol):

            # убираем пару завершенного опциона из заблокированных
            if option_symbol not in self.block_mt_pairs:
                logging.error(
                    f"Не найдена пара '{option_symbol}' в block_mt_pairs: {self.block_mt_pairs}")
            else:
                self.block_mt_pairs.remove(option_symbol)

            mt4_pair, mt4_direct = self.MT4_SIGNALS["type_2"][option_symbol]

            # Сохраняем в статистику
            additional_data = {
                "percentage": self.pair_list['pair_list'].get(mt4_pair)["percent"] if self.pair_list['pair_list'].get(
                    mt4_pair) else "-",
                "account_type": self.account_type,
                "direction": mt4_direct,
                "option_result_word": option_result_word, "loss_refund": loss_refund
            }
            # add_option_to_statistic(option_data, additional_data)

            # Обновляем статистику
            self.window.btn_apply.click()

            # Обновляем счетчик
            if option_result_word == 'loss':
                jump_to = self.deal_series[self.COUNTERS["type_2"][option_symbol]]["on_loss"] - 1
            elif option_result_word == 'win':
                jump_to = self.deal_series[self.COUNTERS["type_2"][option_symbol]]["on_win"] - 1
            else:
                # Если "="
                jump_to = self.COUNTERS["type_2"][option_symbol]

            # Меняем счетчик
            self.COUNTERS["type_2"][option_symbol] = jump_to

            if self.COUNTERS["type_2"][option_symbol] >= len(self.deal_series):
                logging.debug(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена. (Конец таблицы)")
                self.window.log_message(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена.")
                return

            if self.COUNTERS["type_2"][option_symbol] == -1:
                # Если пользователь указал 0 в "перейти к" (тут это -1), то останавливаем серию
                logging.debug(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена (Пользователь указал конец)")
                self.window.log_message(
                    f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена.")
                return

            self.process_option(new_serial=False, counter=self.COUNTERS["type_2"][option_symbol], mt4_pair=mt4_pair,
                                mt4_direct=mt4_direct)

        elif self.window.selected_mm_mode == 3 and self.MT4_SIGNALS["type_3"].get(option_symbol):

            # убираем пару завершенного опциона из заблокированных
            if option_symbol not in self.block_mt_pairs:
                logging.error(
                    f"Не найдена пара '{option_symbol}' в  block_mt_pairs: {self.block_mt_pairs}")
            else:
                self.block_mt_pairs.remove(option_symbol)

            mt4_pair, mt4_direct = self.MT4_SIGNALS["type_3"][option_symbol]

            # Сохраняем в статистику
            additional_data = {
                "percentage": self.pair_list['pair_list'].get(mt4_pair)["percent"] if self.pair_list['pair_list'].get(
                    mt4_pair) else "-",
                "account_type": self.account_type,
                "direction": mt4_direct,
                "option_result_word": option_result_word, "loss_refund": loss_refund
            }
            # add_option_to_statistic(option_data, additional_data)

            # Обновляем статистику
            self.window.btn_apply.click()

            # Обновляем счетчик
            if option_result_word == 'loss':
                jump_to = self.deal_series[self.COUNTERS["type_3"]]["on_loss"] - 1
            elif option_result_word == 'win':
                jump_to = self.deal_series[self.COUNTERS["type_3"]]["on_win"] - 1
            else:
                # Если "="
                jump_to = self.COUNTERS["type_3"]

            if jump_to >= len(self.deal_series):
                logging.debug(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена. (Конец таблицы)")
                self.window.log_message(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена.")
                return

            if jump_to == -1:
                # Если пользователь указал 0 в "перейти к" (тут это -1), то останавливаем серию
                logging.debug(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена (Пользователь указал конец)")
                self.window.log_message(
                    f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена.")
                return

            # Меняем счетчик
            self.COUNTERS["type_3"] = jump_to

            if self.COUNTERS["type_3"] >= len(self.deal_series):
                logging.debug(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена (конец таблицы)")
                self.window.log_message(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена.")
                # Обнуления счетчика режима 4 по этой паре
                self.COUNTERS["type_3"] = 0
                return

            if self.COUNTERS["type_3"] == -1:
                # Если пользователь указал 0 в "перейти к" (тут это -1), то останавливаем серию
                logging.debug(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена (Пользователь указал конец)")
                self.window.log_message(
                    f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена.")
                self.COUNTERS["type_3"] = 0
                return

        elif self.window.selected_mm_mode == 4 and self.MT4_SIGNALS["type_4"].get(option_symbol):

            # убираем пару завершенного опциона из заблокированных
            if option_symbol not in self.block_mt_pairs:
                logging.error(
                    f"Не найдена пара '{option_symbol}' в  block_mt_pairs: {self.block_mt_pairs}")
            else:
                self.block_mt_pairs.remove(option_symbol)

            mt4_pair, mt4_direct = self.MT4_SIGNALS["type_4"][option_symbol]

            # Сохраняем в статистику
            additional_data = {
                "percentage": self.pair_list['pair_list'].get(mt4_pair)["percent"] if self.pair_list['pair_list'].get(
                    mt4_pair) else "-",
                "account_type": self.account_type,
                "direction": mt4_direct,
                "option_result_word": option_result_word, "loss_refund": loss_refund
            }
            # add_option_to_statistic(option_data, additional_data)

            # Обновляем статистику
            self.window.btn_apply.click()

            # Обновляем счетчик
            if option_result_word == 'loss':
                jump_to = self.deal_series[self.COUNTERS["type_4"][mt4_pair]]["on_loss"] - 1
            elif option_result_word == 'win':
                jump_to = self.deal_series[self.COUNTERS["type_4"][mt4_pair]]["on_win"] - 1
            else:
                # Если "="
                jump_to = self.COUNTERS["type_4"][mt4_pair]

            if jump_to >= len(self.deal_series):
                logging.debug(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена. (Конец таблицы)")
                self.window.log_message(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена.")
                return

            if jump_to == -1:
                # Если пользователь указал 0 в "перейти к" (тут это -1), то останавливаем серию
                logging.debug(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена (Пользователь указал конец)")
                self.window.log_message(
                    f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена.")
                return

            # Меняем счетчик
            self.COUNTERS["type_4"][mt4_pair] = jump_to

            if self.COUNTERS["type_4"][mt4_pair] >= len(self.deal_series):
                logging.debug(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена (конец таблицы)")
                self.window.log_message(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена.")
                self.COUNTERS["type_4"][mt4_pair] = 0
                return

            if self.COUNTERS["type_4"][mt4_pair] == -1:
                # Если пользователь указал 0 в "перейти к" (тут это -1), то останавливаем серию
                logging.debug(f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена (Пользователь указал конец)")
                self.window.log_message(
                    f"Серия опционов ({mt4_pair}:{mt4_direct}) завершена.")
                self.COUNTERS["type_4"][mt4_pair] = 0
                return
        else:
            logging.error("Завершен неизвестный опцион.")
            logging.debug(f"{self.MT4_SIGNALS=}")
            logging.debug(f"{self.block_mt_pairs=}")

    # ______ UTEBOT: ______

    def on_open(self, ws):
        self.is_connected = True
        pass

    def on_message(self, ws, message):
        try:
            # Handle initial connection messages
            if not self.connection_established.is_set():
                self.serv_answ.append(message)
                if len(self.serv_answ) >= 2:
                    self.connection_established.set()

            # Check pending requests
            for req_id, (event, condition, response_container) in list(self.pending_requests.items()):
                if condition(message):
                    response_container['response'] = message  # Store the response
                    event.set()  # Set the event to indicate response is received
                    del self.pending_requests[req_id]
                    break

            # Process message
            try:
                data = json.loads(message)
                if "i_balance" in data:
                    logging.debug("i_balance")
                    logging.debug(data)
                    self.ute_data = data

                if "finish_option" in data:
                    logging.debug("finish_option")
                    logging.debug(data)
                    self.option_finished(data)

                if "info_open_option" in data:
                    logging.debug("info_open_option")
                    logging.debug(data)
                    if data.get("api_massive_option", [{}])[0].get("option_id") not in [
                        d.get("api_massive_option", [{}])[0].get("option_id") for d in self.last_opened_options_data]:
                        self.last_opened_options_data.append(data)

            except json.JSONDecodeError:
                pass

        except Exception:
            logging.exception("Exception occurred")

    def on_close(self, ws, close_status_code, close_msg):
        self.is_connected = False
        self.stop_event.set()

    def on_error(self, ws, error):
        self.connection_established.set()
        logging.exception("Exception occurred")

    def _send_request(self, message, condition):
        req_id = str(uuid.uuid4())
        event = threading.Event()
        response_container = {}  # Container for the response
        self.pending_requests[req_id] = (event, condition, response_container)

        try:
            self.ws.send(message)  # Send the message to the WebSocket server
        except WebSocketConnectionClosedException:
            self.reconnect()  # If the connection is closed, attempt to reconnect
            self.ws.send(message)

        # Wait for the response or timeout
        if not event.wait(timeout=4):
            del self.pending_requests[req_id]
            raise TimeoutError("Request timed out")

        # Return the response stored in the container
        return response_container.get('response')

    def reconnect(self):
        self.ws.close()
        self.ws = WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_close=self.on_close,
            on_error=self.on_error
        )
        self.ws_thread = threading.Thread(target=self.ws.run_forever,
                                          kwargs={'sslopt': {"cert_reqs": ssl.CERT_NONE}})
        self.ws_thread.start()
        self.connection_established.clear()
        if not self.connection_established.wait(timeout=10):
            raise ConnectionError("Reconnection failed")

    def get_only_pair_list(self):
        logging.debug("get_only_pair_list")

        def pair_list_condition(msg):
            return "pair_list" in msg

        response = self._send_request("only_pair_list", pair_list_condition)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logging.error(response)
            logging.exception("Exception occurred")
            raise Exception("Ошибка декодирования only_pair_list")

    def open_option(self, pair_name, up_dn, sum_option, type_account,
                    time_h, time_m, time_s, percent_par, w_type_exp):
        message = (
            f"option_send:{pair_name}:{up_dn}:lifetime:{type_account}:"
            f"{sum_option}:0:{w_type_exp}:{time_h}:"
            f"{time_m}:{time_s}:0:ute_bot"
        )
        logging.debug(message)

        def response_condition(msg):
            return 'Error' in msg or 'i_balance' in msg

        response = self._send_request(message, response_condition)

        if 'Error' in response:
            error_key = list(ast.literal_eval(response).keys())[0]
            error_msg = exeptions_determniant(error_key)
            self.serv_answ.append(error_msg)
            logging.debug(error_msg)
        else:
            try:
                self.serv_answ.append("Deal open")

                threading.Thread(
                    target=self._handle_pending_option_async,
                    args=(pair_name, up_dn, sum_option, time_h, time_m, time_s, percent_par),
                    daemon=True
                ).start()

                logging.debug("Deal opened successfully")
                return json.loads(response)
            except json.JSONDecodeError:
                self.serv_answ.append("Unknown response format")

    def ping_serv(self):
        while not self.stop_event.is_set():
            try:
                self.ws.send("ping_us")
            except Exception as e:
                if not self.stop_event.is_set():
                    self.reconnect()
                    logging.debug("reconnection...")
            time.sleep(2)

    def close_connection(self):
        logging.debug("Closing...")
        try:
            self.stop_event.set()
            self.ws.close()
            self.ping_thread.join()
            self.ws_thread.join()
        except Exception:
            logging.exception("Exception closing connection")
            logging.exception("Exception occurred")

    def get_balance(self, account_type):
        if account_type == "demo":
            return self.ute_data.get("m_demo")
        elif account_type == "real_dollar":
            return self.ute_data.get("m_dollar")
        elif account_type == "real_rub":
            return self.ute_data.get("m_rub")
        return None


if __name__ == '__main__':
    url = "wss://2ute.ru:100"
    token = "8f21b220ff1d338ac7d5f38849b43a669bd22030"
    user_id = "14669"
