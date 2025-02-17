from loggingfile import logging
from programm_files import load_money_management_data, load_auth_data
from trading import TradingBot

TYPE_ACCOUNT = {
    'Демо счёт': 'demo',
    'Реальный долларовый': 'real_dollar',
    'Реальный рублёвый': 'real_rub',
}


class OptionSeries():
    def __init__(self, mt4_data, mm_data, auth_data, ute_bot, window):
        self.ute_bot = ute_bot
        self.window = window
        self.account_type = TYPE_ACCOUNT[auth_data["selected_type_account"]]
        self.mt4_pair = mt4_data["pair"]
        self.mt4_direct = mt4_data['direct']
        self.deal_series = []
        for key, item in mm_data.items():
            self.deal_series.append(item)
        print(self.deal_series)
        self.start_series()

    def start_series(self):
        deal = self.deal_series[0]

        self.ute_bot.get_only_pair_list()
        pair_list = self.ute_bot.serv_answ[(-1)]
        self.window.log_message(f"Открытие опциона - {self.mt4_pair}:{self.mt4_direct}...")
        if self.mt4_pair in pair_list['pair_list']:
            if int(pair_list['pair_list'][self.mt4_pair]['percent']) >= int(deal["filter_payment"].replace("%", "")):
                self.bot.open_option(pair_name=self.mt4_pair, up_dn=self.mt4_direct.lower(),
                                     sum_option=deal["investment"],
                                     type_account=self.account_type, time_h=deal_time[0],
                                     time_m=deal_time[1],
                                     time_s=deal_time[2], percent_par=0)
                self.window.log_message(self.bot.serv_answ[(-1)])
                logging.info('Option open')
            else:  # inserted
                self.window.log_message('Less than pay filter')
                logging.info('Less than pay filter')
        else:  # inserted
            self.window.log_message(f"{self.mt4_pair} not exist")
            logging.warning(f"{self.mt4_pair} not exist")

    def open_option(self):
        pass


def start_series(mt4_data: dict, ute_bot: TradingBot, window):
    mm_data = load_money_management_data()
    auth_data = load_auth_data()
    OptionSeries(mt4_data, mm_data, auth_data, ute_bot, window)
