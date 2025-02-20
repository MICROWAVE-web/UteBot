import datetime

import pytz

from loggingfile import logging
from programm_files import load_money_management_data

from mm_types import TYPE_ACCOUNT



class OptionSeries:
    def __init__(self, auth_data, ute_bot, window):
        mm_data = load_money_management_data()
        self.ute_bot = ute_bot
        self.window = window
        self.account_type_russ = auth_data["selected_type_account"]
        self.account_type = TYPE_ACCOUNT[auth_data["selected_type_account"]]

        self.deal_series = []
        for key, item in mm_data.items():
            self.deal_series.append(item)

        # Вывод списка ММ таблицы
        logging.debug(f"{self.deal_series}")

        # Счётчик строк таблицы
        self.row_counter = 0

    def count_expiration_type_1(self, candle_long_in_minutes):
        current_time = datetime.datetime.now(pytz.utc)
        current_time = current_time.astimezone(pytz.timezone('Etc/GMT-3'))
        logging.debug(f"Текущее время utc+3: {current_time=}")
        divisors = list(range(0, 121, candle_long_in_minutes))
        data_with_limit = current_time + datetime.timedelta(seconds=1)
        logging.debug(f"Текущее время + минута и 1 секунды: {data_with_limit=}")
        for d in divisors:
            h = 0
            if d >= 60:
                h += 1
                d -= 60
            new_data = current_time.replace(minute=d, second=0, microsecond=0) + datetime.timedelta(hours=h)

            if new_data > data_with_limit:
                return new_data.strftime('%H:%M:%S')  # Возвращаем найденный делитель

    def mt4_signal(self, mt4_data: dict):
        # Данные из МТ4
        mt4_pair = mt4_data["pair"]
        mt4_direct = mt4_data['direct']

        # Провера типа ММ и наличия активных открытых опционов
        logging.debug(f"{self.window.selected_mm_mode=}")
        logging.debug(f"{self.ute_bot.have_active_options=}")
        if self.window.selected_mm_mode == 3 and self.ute_bot.have_active_options is True:
            text = f"{mt4_pair} сделка не открыта, есть открытый опцион по {mt4_pair}"
            self.window.log_message(text)
            logging.debug(text)
            return

        if self.window.selected_mm_mode == 4 and self.ute_bot.have_active_options is False:
            self.row_counter = 0
        elif self.window.selected_mm_mode == 4 and self.ute_bot.have_active_options is True:
            self.row_counter += 1
            if self.row_counter >= len(self.deal_series):
                self.row_counter = 0

        deal = self.deal_series[self.row_counter]
        logging.debug(f"{deal=}")

        # Проверка стоп тейк
        take_profit = deal['take_profit']
        stop_loss = deal['stop_loss']
        account_balance = self.ute_bot.get_balance(account_type=self.account_type)

        logging.debug(f"{take_profit=}")
        logging.debug(f"{stop_loss=}")
        logging.debug(f"{account_balance=}")

        take_profit = float(take_profit)
        stop_loss = float(stop_loss)
        account_balance = float(account_balance)

        if account_balance >= take_profit:
            self.window.log_message(
                f"Баланс превысил <span style='color:green'>Тейк профит</span>. Открытие опциона ({mt4_pair}:{mt4_direct}) остановлено.")
            return
        elif account_balance <= stop_loss:
            self.window.log_message(
                f"Баланс меньше <span style='color:red'>Стоп лосс</span>. Открытие опциона ({mt4_pair}:{mt4_direct}) остановлено.")
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
                f"Баланс сделки (${investment}) не удовлетворяет условиям для открытия опциона ({mt4_pair}:{mt4_direct}) на аккаунте «{self.account_type_russ}». (мин 0.1 макс 2,000)")
            return
        elif self.account_type == 'real_rub' and not (20 <= investment <= 200000):
            self.window.log_message(
                f"Баланс сделки (${investment}) не удовлетворяет условиям для открытия опциона ({mt4_pair}:{mt4_direct}) на аккаунте «{self.account_type_russ}». (мин 20 макс 200,000)")
            return

        # Обработка экспирации
        if ':' in deal["expiration"]:
            w_type_exp = "2"
            deal_time = deal["expiration"].split(':')

        else:
            w_type_exp = "1"
            deal_time = self.count_expiration_type_1(int(deal["expiration"])).split(':')
        logging.debug(f"{deal_time=}")

        pair_list = self.ute_bot.get_only_pair_list()
        logging.debug(f"{pair_list=}")
        self.window.log_message(f"Открытие опциона... ({mt4_pair}:{mt4_direct})")
        if mt4_pair in pair_list['pair_list']:
            if int(pair_list['pair_list'][mt4_pair]['percent']) >= int(deal["filter_payment"].replace("%", "")):

                if len(deal_time) == 3:
                    self.ute_bot.open_option(pair_name=mt4_pair, up_dn=mt4_direct.lower(),
                                             sum_option=deal["investment"],
                                             type_account=self.account_type, time_h=deal_time[0],
                                             time_m=deal_time[1],
                                             time_s=deal_time[2], percent_par=0, w_type_exp=w_type_exp)
                    self.window.log_message(
                        'Опцион открыт' if "Deal open" in str(self.ute_bot.serv_answ[(-1)]) else str(
                            self.ute_bot.serv_answ[(-1)]))
                    logging.info('Option open')

            else:
                self.window.log_message(
                    f"Less than pay filter ({int(pair_list['pair_list'][mt4_pair]['percent'])}%)")
                logging.info(f"Less than pay filter ({int(pair_list['pair_list'][mt4_pair]['percent'])}%)")
        else:
            self.window.log_message(f"{mt4_pair} not exist")
            logging.warning(f"{mt4_pair} not exist")

    def open_option(self):
        pass
