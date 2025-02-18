import ast
import json
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
        if not self.connection_established.wait(timeout=10):
            raise ConnectionError("Connection timeout")

        # Start ping thread
        self.ping_thread = threading.Thread(target=self.ping_serv)
        self.ping_thread.daemon = True
        self.ping_thread.start()

    def on_open(self, ws):
        pass

    def on_message(self, ws, message):
        try:
            # Handle initial connection messages
            if not self.connection_established.is_set():
                self.serv_answ.append(message)
                if len(self.serv_answ) >= 2:
                    self.connection_established.set()

            # Check pending requests
            for req_id, (event, condition) in list(self.pending_requests.items()):
                if condition(message):
                    event.set()
                    del self.pending_requests[req_id]
                    break

            # Update balance data
            try:
                data = json.loads(message)
                if "i_balance" in data:
                    self.ute_data = data
            except json.JSONDecodeError:
                pass

        except Exception as e:
            traceback.print_exc()

    def on_close(self, ws, close_status_code, close_msg):
        self.stop_event.set()

    def on_error(self, ws, error):
        self.connection_established.set()
        self.stop_event.set()
        traceback.print_exc()

    def _send_request(self, message, condition):
        req_id = str(uuid.uuid4())
        event = threading.Event()
        self.pending_requests[req_id] = (event, condition)

        try:
            self.ws.send(message)
        except WebSocketConnectionClosedException:
            self.reconnect()
            self.ws.send(message)

        if not event.wait(timeout=10):
            del self.pending_requests[req_id]
            raise TimeoutError("Request timed out")
        return event.response

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
        def pair_list_condition(msg):
            return "pair_list" in msg

        self._send_request("only_pair_list", pair_list_condition)

        # Process responses
        pair_list = None
        start_time = time.time()
        while time.time() - start_time < 10:
            for msg in self.serv_answ:
                if "pair_list" in msg:
                    pair_list = ast.literal_eval(msg)
                    self.serv_answ.append(pair_list)
                    return pair_list
            time.sleep(0.1)
        raise TimeoutError("Failed to get pair list")

    def open_option(self, pair_name, up_dn, sum_option, type_account,
                    time_h, time_m, time_s, percent_par):
        w_type_exp = "2"
        message = (
            f"option_send:{pair_name}:{up_dn}:lifetime:{type_account}:"
            f"{sum_option}:{percent_par}:{w_type_exp}:{time_h}:"
            f"{time_m}:{time_s}:0:ute_bot"
        )

        def response_condition(msg):
            return 'Error' in msg or 'i_balance' in msg

        response = self._send_request(message, response_condition)

        if 'Error' in response:
            error_key = list(ast.literal_eval(response).keys())[0]
            error_msg = exeptions_determniant(error_key)
            self.serv_answ.append(error_msg)
            print(error_msg)
        else:
            try:
                self.ute_data = json.loads(response)
                self.serv_answ.append("Deal open")
                print("Deal opened successfully")
            except json.JSONDecodeError:
                self.serv_answ.append("Unknown response format")

    def ping_serv(self):
        while not self.stop_event.is_set():
            try:
                self.ws.send("ping_us")
            except Exception as e:
                if not self.stop_event.is_set():
                    self.reconnect()
            time.sleep(30)

    def close_connection(self):
        self.stop_event.set()
        self.ws.close()
        self.ping_thread.join()
        self.ws_thread.join()


if __name__ == '__main__':
    pass