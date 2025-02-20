import ast
import json
import logging
import ssl
import threading
import time
import traceback
import uuid

from websocket import WebSocketApp, WebSocketConnectionClosedException


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


class TradingBot:
    def __init__(self, url, userid, token):
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
        self._last_opened_option_id = None
        self.have_active_options = False

        # Последний опцион для коллбека в mm_trading.py
        self._last_finished_option = None
        self._observers = []

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
                        self.last_opened_option_id = option_key
                    print(self.active_options)

                if "finish_option" in data:
                    try:
                        logging.debug(f"OPTION FINISHED: {data}")
                        option_key = str(data["info_finish_option"][0]["option_id"])
                        if option_key in self.active_options.keys():
                            print(self.active_options)
                            self.active_options.pop(option_key)
                            if len(self.active_options.keys()) == 0:
                                self.have_active_options = False
                            self.last_finished_option = data["info_finish_option"][0]
                            print(self.active_options)
                            print(self.last_finished_option)

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
            self.ws.send(message)
        except WebSocketConnectionClosedException:
            self.reconnect()
            self.ws.send(message)

        if not event.wait(timeout=4):
            del self.pending_requests[req_id]
            raise TimeoutError("Request timed out")

        # Return the stored response from the container
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

    def add_observer(self, observer):
        self._observers.append(observer)
        print(self._observers)

    def notify_observers(self, type_notify=""):
        print("Возвращаем результаты")
        print(self._observers)
        for observer in self._observers:
            if type_notify == "finish":
                observer.option_finished(self._last_finished_option)
            elif type_notify == "open":
                observer.last_opened_option_id = self._last_opened_option_id

    @property
    def last_finished_option(self):
        return self._last_finished_option

    @last_finished_option.setter
    def last_finished_option(self, new_value):
        self._last_finished_option = new_value
        self.notify_observers(type_notify="finish")

    @property
    def last_opened_option_id(self):
        return self._last_opened_option_id

    @last_opened_option_id.setter
    def last_opened_option_id(self, new_value):
        self._last_opened_option_id = new_value
        self.notify_observers(type_notify="open")


if __name__ == '__main__':
    url = "wss://2ute.ru:100"
    token = "8f21b220ff1d338ac7d5f38849b43a669bd22030"
    user_id = "14669"
    bot = TradingBot(url=url, token=token, userid=user_id)
    print(bot.get_only_pair_list())
    print(bot.get_only_pair_list())
