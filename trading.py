import ast
import json
import ssl
import threading
import time
import traceback

from websocket import create_connection, _exceptions


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

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        self.url = f"{url}/?userId={userid}&token={token}"

        self.serv_answ = []
        try:
            self.client = create_connection(self.url, sslopt={"cert_reqs": ssl.CERT_NONE})
            self.serv_answ.append(self.client.recv_data())
            self.serv_answ.append(self.client.recv_data())
            for i in self.serv_answ:
                print(i)
            print('connect set')
        except _exceptions.WebSocketConnectionClosedException:
            self.client = None
            self.serv_answ.append(False)
        except Exception as ex:
            print(1, ex)
            self.client = None
            self.serv_answ.append(False)

        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.ping_serv)
        self.thread.start()

    def get_only_pair_list(self):
        self.client.send("only_pair_list")

        resp = ast.literal_eval(self.client.recv_data()[1].decode())

        while True:
            if type(resp) != int and "pair_list" in resp:
                break
            resp = ast.literal_eval(self.client.recv_data()[1].decode())

        print(1, resp)
        self.serv_answ.append(resp)

    def open_option(self, pair_name, up_dn, sum_option, type_account, time_h, time_m, time_s, percent_par):
        w_type_exp = "2"
        self.client.send(
            f"option_send:{pair_name}:{up_dn}:lifetime:{type_account}:{sum_option}:{percent_par}:{w_type_exp}:{time_h}:{time_m}:{time_s}:0:ute_bot")

        self.serv_answ.append(self.client.recv_data())
        if 'Error' in self.serv_answ[-1][1].decode():
            el = ast.literal_eval(self.serv_answ[-1][1].decode())
            el = list(el.keys())[0]
            self.serv_answ.append(exeptions_determniant(el))

        else:
            print(self.serv_answ[-1])
            self.serv_answ.append("Deal open")
        self.client.recv_data()

    def ping_serv(self):
        if self.client:
            while not self.stop_event.is_set():
                if self.client:
                    self.client.send("ping_us")
                    print(self.client.recv_data())
                else:
                    break
                if not self.stop_event.is_set():
                    time.sleep(30)
                else:
                    break

    def close_connection(self):
        self.client.close()
        self.client = None
        self.stop_event.set()  # Выставляем флаг остановки


if __name__ == '__main__':
    # Тестирование запросом на разрешение подключения
    url = 'wss://2ute.ru:100'
    token = 'c1c61ddacfdc253c7f3f43e1a093977d1de19a79'
    user_id = '14735'

    ALLOWED_PARTNER_IDS = ["111-116", "777-13269"]
    verified = False
    try:
        bot = TradingBot(url=url, token=token, userid=user_id)
        for answer_object in bot.serv_answ:
            answer_text = answer_object[1].decode()
            if "partner_id" not in answer_text:
                continue
            d = json.loads(answer_text)
            if d["partner_id"] in ALLOWED_PARTNER_IDS:
                verified = True
                break

    except Exception as ex:
        traceback.print_exc()
        # return False

    print(52, verified)
