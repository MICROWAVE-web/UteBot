import ast
import json
import ssl
import threading
import time
import traceback
import uuid
from datetime import timedelta

from websocket import WebSocketApp, WebSocketConnectionClosedException

from loggingfile import logging
from mm_types import TYPE_ACCOUNT
from programm_files import load_money_management_data
from utils import get_expiration, check_availability_time_range


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

        self.window = window
        self.account_type_russ = auth_data["selected_type_account"]
        self.account_type = TYPE_ACCOUNT[auth_data["selected_type_account"]]

        # Счётчик строк таблицы
        self.COUNTERS = {
            "type_1": {},  # Храним id текущих опционов: индекс в таблице, при переходе к слудющему, удаляем старый.
            "type_2": {},  # Храним id текущих опционов: индекс в таблице, при переходе к слудющему, удаляем старый.
            "type_3": 0,
            "type_4": 0
        }

        self.row_counter = 0

        self.mt4_pair = None
        self.mt4_direct = None

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

        self.active_options = {}
        self.last_opened_option = None
        self.have_active_options = False
        self.block_mt_requests = False

        # Последний опцион
        self.last_finished_option = None

        self.deal_series = []

        self.update_mm_data()

    def update_mm_data(self):
        mm_data = load_money_management_data()
        self.deal_series = []
        for key, item in mm_data.items():
            self.deal_series.append(item)

        # Вывод списка ММ таблицы
        logging.debug(f"{self.deal_series}")

    def mt4_signal(self, mt4_data: dict):
        self.update_mm_data()
        # Данные из МТ4
        self.mt4_pair = mt4_data["pair"]
        self.mt4_direct = mt4_data['direct']

        # Провера типа ММ и наличия активных открытых опционов
        logging.debug(f"{self.window.selected_mm_mode=}")
        logging.debug(f"{self.have_active_options=}")
        if self.window.selected_mm_mode == 4 and self.have_active_options is True:
            text = f"{self.mt4_pair} сделка не открыта, есть открытый опцион по {self.mt4_pair}"
            self.window.log_message(text)
            logging.debug(text)
            return

        if self.block_mt_requests is True:
            text = f"{self.mt4_pair} сделка не открыта, приём сигналов из MT4 приостановлен."
            self.window.log_message(text)
            logging.debug(text)
            return

        elif self.window.selected_mm_mode == 4 and self.have_active_options is False:
            # В скоре будет открыт опцион с режимом 4. В этом режиме запрещён прием сигналов до окончания текущей
            # серии опционов
            self.block_mt_requests = True



        # if self.window.selected_mm_mode == 1 and self.have_active_options is False:
        #    self.row_counter = 0
        elif self.window.selected_mm_mode == 1:
            self.row_counter += 1
            if self.row_counter >= len(self.deal_series):
                self.row_counter = 0

        self.process_option(new_serial=True)

    def process_option(self, new_serial=False):
        self.reconnect()

        # Проверка на интервалы сниженной выплаты
        max_serial_time_long = timedelta()
        for deal in self.deal_series:
            expiration_data = get_expiration(deal)
            max_serial_time_long += expiration_data["time_delta"]

        if not check_availability_time_range(max_serial_time_long):
            self.window.log_message(
                f"Серия опционов пересекается с расписанием снижения выплат. Открытие опциона ({self.mt4_pair}:{self.mt4_direct}) остановлено.")
            return

        # Получение текущей сделки
        deal = self.deal_series[self.row_counter]
        logging.debug(f"{deal=}")

        # Проверка стоп тейк
        take_profit = deal['take_profit']
        stop_loss = deal['stop_loss']
        account_balance = self.get_balance(account_type=self.account_type)

        logging.debug(f"{take_profit=}")
        logging.debug(f"{stop_loss=}")
        logging.debug(f"{account_balance=}")

        take_profit = float(take_profit)
        stop_loss = float(stop_loss)
        account_balance = float(account_balance)

        if account_balance >= take_profit:
            self.window.log_message(
                f"Баланс превысил <span style='color:green'>Тейк профит</span>. Открытие опциона ({self.mt4_pair}:{self.mt4_direct}) остановлено.")
            return
        elif account_balance <= stop_loss:
            self.window.log_message(
                f"Баланс меньше <span style='color:red'>Стоп лосс</span>. Открытие опциона ({self.mt4_pair}:{self.mt4_direct}) остановлено.")
            return

        # Проверка investment
        if "%" in deal["investment"]:
            investment = round(account_balance * float(deal["investment"].replace("%", "")) / 100.0, 1)
        else:
            investment = round(float(deal["investment"]), 1)

        # Проверка суммы сделки (Счёт доллар - мин 0.1 макс 2,000 \ Счёт рубль - мин 20 макс 200,000)
        logging.debug(f"{investment=}")
        if self.account_type == 'real_dollar' and not (0.1 <= investment <= 2000):
            self.window.log_message(
                f"Баланс сделки (${investment}) не удовлетворяет условиям для открытия опциона ({self.mt4_pair}:{self.mt4_direct}) на аккаунте «{self.account_type_russ}». (мин 0.1 макс 2,000)")
            return
        elif self.account_type == 'real_rub' and not (20 <= investment <= 200000):
            self.window.log_message(
                f"Баланс сделки (₽{investment}) не удовлетворяет условиям для открытия опциона ({self.mt4_pair}:{self.mt4_direct}) на аккаунте «{self.account_type_russ}». (мин 20 макс 200,000)")
            return

        # Обработка экспирации
        expiration_data = get_expiration(deal)
        deal_time = expiration_data["deal_time"]
        w_type_exp = expiration_data["w_type_exp"]

        pair_list = self.get_only_pair_list()
        logging.debug(f"{pair_list=}")
        self.window.log_message(f"Открытие опциона... ({self.mt4_pair}:{self.mt4_direct})")
        if self.mt4_pair in pair_list['pair_list']:
            if int(pair_list['pair_list'][self.mt4_pair]['percent']) >= int(deal["filter_payment"].replace("%", "")):

                if len(deal_time) == 3:
                    self.open_option(pair_name=self.mt4_pair, up_dn=self.mt4_direct.lower(),
                                     sum_option=deal["investment"],
                                     type_account=self.account_type, time_h=deal_time[0],
                                     time_m=deal_time[1],
                                     time_s=deal_time[2], percent_par=0, w_type_exp=w_type_exp)
                    self.window.log_message(
                        f'Опцион открыт. Пара: {self.mt4_pair}, Направление: {self.mt4_direct}, Инвестиция: {deal["investment"]}, '
                        f'Экспирация: {deal["expiration"]} (Тип {w_type_exp}), Строка {self.row_counter + 1}.'
                        if "Deal open" in str(self.serv_answ[(-1)]) else str(self.serv_answ[(-1)]))
                    logging.info('Option open')

            else:
                self.window.log_message(
                    f"Less than pay filter ({int(pair_list['pair_list'][self.mt4_pair]['percent'])}%)")
                logging.info(f"Less than pay filter ({int(pair_list['pair_list'][self.mt4_pair]['percent'])}%)")
        else:
            self.window.log_message(f"{self.mt4_pair} not exist")
            logging.warning(f"{self.mt4_pair} not exist")

    def option_finished(self, option_data):
        last_finished_option_key = str(self.last_finished_option["option_id"])
        last_opened_option_key = str(self.last_opened_option["option_id"])

        if last_finished_option_key == last_opened_option_key:
            logging.debug("Опцион завершен!")
            if self.window.selected_mm_mode == 4 and self.have_active_options is False:
                if self.row_counter >= len(self.deal_series):
                    logging.debug("Серия опционов завершена (конец таблицы)")
                    self.window.log_message("Серия опционов завершена (конец таблицы)")
                    return
                if (option_data["info_finish_option"][0]["finish_current_result"].lower() != "=") or (
                        option_data["info_finish_option"][0]["finish_current_result"].lower() !=
                        self.deal_series[self.row_counter + 1]["result_type"].lower()):
                    logging.debug("Серия завершена (Невыполнение условий результата)")
                    self.window.log_message("Серия завершена (Невыполнение условий результата)")
                    return
                self.row_counter += 1
                self.process_option(new_serial=False)
        else:
            logging.debug("Завершен не последний опцион")

    # ______ UTEBOT: ______

    def on_open(self, ws):
        self.is_connected = True
        pass

    def on_message(self, ws, message):
        try:
            logging.debug(message)
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

            # Update balance data
            try:
                data = json.loads(message)
                if "i_balance" in data:
                    self.ute_data = data
                if "api_massive_option" in data:
                    option_key = str(data["api_massive_option"][0]["option_id"])
                    if option_key not in self.active_options:
                        self.active_options[option_key] = data["api_massive_option"][0]
                        self.have_active_options = True
                        self.last_opened_option = data["api_massive_option"][0]
                        self.last_finished_option = None

                if "finish_option" in data:
                    try:
                        logging.debug(f"OPTION FINISHED: {data}")
                        option_key = str(data["info_finish_option"][0]["option_id"])
                        if option_key in self.active_options.keys():
                            self.active_options.pop(option_key)
                            if len(self.active_options.keys()) == 0:
                                self.have_active_options = False
                                self.block_mt_requests = False
                                # Разрешает приём запросов из МТ4
                            self.last_finished_option = data["info_finish_option"][0]
                            self.option_finished(data)

                    except KeyError:
                        traceback.print_exc()

            except json.JSONDecodeError:
                pass

        except Exception:
            traceback.print_exc()

    def on_close(self, ws, close_status_code, close_msg):
        self.is_connected = False
        self.stop_event.set()

    def on_error(self, ws, error):
        self.connection_established.set()
        self.stop_event.set()
        traceback.print_exc()

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

        responce = self._send_request("only_pair_list", pair_list_condition)
        try:
            return json.loads(responce)
        except json.JSONDecodeError:
            logging.error(responce)
            traceback.print_exc()
            raise Exception("Ошибка декодирования only_pair_list")

    def open_option(self, pair_name, up_dn, sum_option, type_account,
                    time_h, time_m, time_s, percent_par, w_type_exp):
        message = (
            f"option_send:{pair_name}:{up_dn}:lifetime:{type_account}:"
            f"{sum_option}:{percent_par}:{w_type_exp}:{time_h}:"
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
                self.ute_data = json.loads(response)
                self.serv_answ.append("Deal open")
                logging.debug("Deal opened successfully")
            except json.JSONDecodeError:
                self.serv_answ.append("Unknown response format")

    def ping_serv(self):
        while not self.stop_event.is_set():
            try:
                self.ws.send("ping_us")
            except Exception as e:
                if not self.stop_event.is_set():
                    self.reconnect()
            time.sleep(10)

    def close_connection(self):
        logging.debug("Closing...")
        try:
            self.stop_event.set()
            self.ws.close()
            self.ping_thread.join()
            self.ws_thread.join()
        except Exception:
            logging.exception("Exception closing connection")
            traceback.print_exc()

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
