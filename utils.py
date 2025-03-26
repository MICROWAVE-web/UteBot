import traceback
from datetime import datetime, timedelta
from typing import List

import pytz

from loggingfile import logging
from programm_files import load_statistic_data, save_statistic_data


def get_expiration(deal):
    if ':' in deal["expiration"]:
        w_type_exp = "2"
        deal_time = deal["expiration"].split(':')

        # Разделяем строку на часы, минуты и секунды
        hours, minutes, seconds = map(int, deal["expiration"].split(':'))

        # Создаем объект timedelta
        time_delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    else:
        w_type_exp = "1"
        deal_time = count_expiration_type_1(int(deal["expiration"])).split(':')
        time_delta = timedelta(minutes=int(deal["expiration"]))

    logging.debug(f"{deal_time=}")

    return {
        "w_type_exp": w_type_exp,
        "deal_time": deal_time,
        "time_delta": time_delta
    }


def count_expiration_type_1(candle_long_in_minutes):
    current_time = datetime.now(pytz.utc)
    current_time = current_time.astimezone(pytz.timezone('Etc/GMT-3'))
    logging.debug(f"Текущее время utc+3: {current_time=}")
    divisors = list(range(0, 121, candle_long_in_minutes))
    data_with_limit = current_time + timedelta(seconds=1, minutes=1)
    logging.debug(f"Текущее время + 1 секунда: {data_with_limit=}")
    for d in divisors:
        h = 0
        if d >= 60:
            h += 1
            d -= 60
        new_data = current_time.replace(minute=d, second=0, microsecond=0) + timedelta(hours=h)

        if new_data > data_with_limit:
            return new_data.strftime('%H:%M:%S')  # Возвращаем найденный делитель


# Определяем временные интервалы
time_intervals = [
    ("00:00:00", "05:00:00"),
    ("07:55:00", "08:01:59"),
    ("16:55:00", "17:01:59"),
    ("17:55:00", "18:01:59"),
    ("18:55:00", "19:01:59"),
    ("19:55:00", "20:01:59"),
    ("20:30:00", "23:59:59"),
    # ("20:55:00", "21:01:59"),
    # ("21:55:00", "22:01:59"),
    # ("22:55:00", "23:01:59"),
    # ("23:25:00", "23:31:59"),
]


def parse_datetime(time_str, next_day=False):
    """Парсим строковое время и добавляем день, если нужно. Все датetime объекты будут с привязкой к часовому поясу UTC+3"""
    now = datetime.now(pytz.timezone('Etc/GMT-3'))  # Текущее время в нужной временной зоне
    dt = datetime.strptime(time_str, "%H:%M:%S").replace(year=now.year, month=now.month, day=now.day,
                                                         tzinfo=pytz.timezone(
                                                             'Etc/GMT-3'))  # Привязываем к часовому поясу
    if next_day:
        dt += timedelta(days=1)
    return dt


def check_overlap(point_time, start, end):
    """Проверяем, есть ли пересечение или вхождение двух интервалов."""
    # Сравниваем все объекты с часовым поясом UTC+3
    return start <= point_time <= end


def is_time_interval_in_schedule(point_time, intervals, next_day=False):
    """Проверяем, попадает ли интервал в ежедневное расписание."""
    for start, end in intervals:
        start_time = parse_datetime(start)
        end_time = parse_datetime(end, next_day)

        if check_overlap(point_time, start_time, end_time):
            return True

    return False


def check_weekend_overlap(end_time):
    """Проверка, попадает ли интервал в выходные дни."""
    end_day_of_week = end_time.weekday()

    # Проверка для пятницы-субботы-воскресенья
    if end_day_of_week in [5, 6]:
        return True

    return False


# Функция для проверки доступности в заданном интервале
def check_availability_time_range(serial_start_points: List[timedelta]):
    """Проверка доступности для открытия опциона."""
    # Получаем текущее время в часовом поясе UTC+3
    current_time = datetime.now(pytz.utc)
    current_time = current_time.astimezone(pytz.timezone('Etc/GMT-3'))
    for ind, serial_start_point in enumerate(serial_start_points, start=0):
        point_time = current_time + serial_start_point
        if point_time.day > current_time.day:
            next_day = True
        else:
            next_day = False

        # Проверка на выходные только для пятницы, субботы и воскресенья
        if check_weekend_overlap(point_time):
            return False, "weekend"

        # Проверяем конец серии
        if ind == len(serial_start_points) - 1:
            time_intervals_end = [
                ("00:00:00", "05:00:00"),
                ("20:30:00", "23:59:59"),
            ]
            logging.debug(f"last_time_point: {point_time}")
            if is_time_interval_in_schedule(point_time, time_intervals_end, next_day):
                return False, "low"
        else:
            if is_time_interval_in_schedule(point_time, time_intervals, next_day):
                return False, "low"

    return True, ""


def convert_datetime_format(input_time):
    # Получаем текущий год
    current_year = datetime.now().year

    # Парсим исходную строку, добавляя текущий год
    input_time_with_year = f"{current_year} {input_time}"

    # Преобразуем строку в объект datetime
    time_obj = datetime.strptime(input_time_with_year, "%Y %d %B %H:%M:%S")

    # Форматируем в нужный формат
    formatted_time = time_obj.strftime("%d-%m-%Y %H:%M:%S")

    return formatted_time


def recalculate_summary(data):
    try:
        trades = data["trades"]

        total = len(trades)
        profit = 0
        loss = 0
        refund = 0
        net_profit = 0
        gross_profit = 0
        gross_loss = 0
        avg_profit_trade = 0
        avg_loss_trade = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0

        consecutive_wins = 0
        consecutive_losses = 0

        for trade in trades:
            result = float(trade["result"][:-1])
            # Если обычный возврат ли возврат на -1 пункт - 50%
            if trade["open_price"] == trade["close_price"] or trade.get('loss_refund') is True:
                refund += 1
                # Учитываем возвратв 50% как убыточную сделку
                if result < trade['volume']:
                    gross_loss += result

            elif result > 0:
                profit += 1
                gross_profit += result
                consecutive_wins += 1
                consecutive_losses = 0
            elif result < 0:
                loss += 1
                gross_loss += result
                consecutive_losses += 1
                consecutive_wins = 0

            if consecutive_wins > max_consecutive_wins:
                max_consecutive_wins = consecutive_wins

            if consecutive_losses > max_consecutive_losses:
                max_consecutive_losses = consecutive_losses

        avg_profit_trade = gross_profit / profit if profit > 0 else 0
        avg_loss_trade = gross_loss / loss if loss > 0 else 0

        net_profit = gross_profit + gross_loss

        data["summary"] = {
            "total": round(total, 2),
            "profit": round(profit, 2),
            "loss": round(loss, 2),
            "refund": round(refund, 2),
            "net_profit": round(net_profit, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "avg_profit_trade": round(avg_profit_trade, 2),
            "avg_loss_trade": round(avg_loss_trade, 2),
            "max_consecutive_wins": round(max_consecutive_wins, 2),
            "max_consecutive_losses": round(max_consecutive_losses, 2),
            "winrate": str(round(round(profit / total, 2) * 100)) if total > 0 else "0%"
        }
    except Exception as e:
        logging.exception("Exception occurred")
        return False

    return data


def get_datetime_difference(time_str1, time_str2):
    # Получаем текущий год
    current_year = datetime.now().year

    # Преобразуем строки в объекты datetime
    time1 = datetime.strptime(f"{current_year} {time_str1}", "%Y %d %B %H:%M:%S")
    time2 = datetime.strptime(f"{current_year} {time_str2}", "%Y %d %B %H:%M:%S")

    # Вычисляем разницу
    time_diff = time2 - time1

    # Извлекаем часы, минуты и секунды из разницы
    hours = time_diff.seconds // 3600
    minutes = (time_diff.seconds // 60) % 60
    seconds = time_diff.seconds % 60

    # Выводим разницу в формате "часы:минуты:секунды"
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def add_option_to_statistic(option_data, additional_data):
    def fixed_num(n, prec=6):
        return f"{n:.{prec}f}".rstrip('0')

    # option_data = {"finish_option":"ok","i_balance":"ok","m_dollar":"-0.000","m_dollar_bonus":"0.190",
    # "m_rub":"0.00","m_rub_bonus":"0.30","m_demo":"11525.026","info_finish_option":[{"option_id":1355291,
    # "type_balance":"demo","symbol":"EURAUD","sum":"539.300","sum_pay":"976.133","wait_profit":"436.833",
    # "unix_open":"1741195140","time_open":"05 March 20:19:00","unix_close":1741195200,"time_close":"05 March 20:20:00",
    # "price_open":"1.70768","finish_current_result":"loss","finish_current_result_sum":"-539.300","close_price":"1.70804"}]}
    statistic_data = load_statistic_data()

    loss_refund = additional_data["loss_refund"]

    if additional_data["account_type"] in ["real_dollar", "demo"]:
        money_symbol = "$"
    else:
        money_symbol = "₽"

    info = option_data["info_finish_option"][0]
    open_price = float(info["price_open"])
    close_price = float(info["close_price"])
    finish_current_result = info["finish_current_result"]
    if (open_price < close_price and finish_current_result == 'loss' or
            open_price > close_price and finish_current_result == 'win'):
        direction = 'SELL'
    elif (open_price > close_price and finish_current_result == 'loss' or
          open_price < close_price and finish_current_result == 'win'):
        direction = 'BUY'
    else:
        direction = 'BUY' if additional_data["direction"] == "UP" else "SELL"
    # Добавляем новую сделку
    statistic_data["trades"].append(
        {
            "type_account": additional_data["account_type"],
            "asset": info["symbol"],
            "open_time": convert_datetime_format(info["time_open"]),
            "expiration": get_datetime_difference(info["time_open"], info["time_close"]),
            "close_time": convert_datetime_format(info["time_close"]),
            "open_price": open_price,
            "trade_type": direction,
            "close_price": close_price,
            "points": fixed_num(round(float(info["price_open"]) - float(info["close_price"]), 6)),
            "volume": float(info["sum"]),
            "refund": 0,
            "percentage": str(additional_data["percentage"]) + ("%" if additional_data["percentage"] != "-" else ""),
            "result": f"{round(float(info['finish_current_result_sum']), 6)}{money_symbol}",
            "loss_refund": loss_refund,
        },
    )

    save_statistic_data(statistic_data)



if __name__ == "__main__":
    pass
    # print(count_expiration_type_1(2))
    # statistic_data = load_statistic_data()
    # updated_data = recalculate_summary(statistic_data)
    #  gsave_statistic_data(updated_data)

    ll = [
        timedelta(hours=-8),
        timedelta(hours=-8, minutes=10),
    ]
    check_availability_time_range(ll)
