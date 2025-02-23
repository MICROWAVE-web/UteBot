import re
from datetime import datetime, timedelta

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
            print(new_data.strftime('%H:%M:%S'))
            return new_data.strftime('%H:%M:%S')  # Возвращаем найденный делитель


# Определяем временные интервалы
time_intervals = [
    ("07:55:00", "08:01:59"),
    ("16:55:00", "17:01:59"),
    ("17:55:00", "18:01:59"),
    ("18:55:00", "19:01:59"),
    ("19:55:00", "20:01:59"),
    ("20:55:00", "21:01:59"),
    ("21:55:00", "22:01:59"),
    ("22:55:00", "23:01:59"),
    ("23:25:00", "23:31:59"),
]


def parse_time(time_str):
    return datetime.strptime(time_str, "%H:%M:%S").time()


def check_overlap(start1, end1, start2, end2):
    return max(start1, start2) <= min(end1, end2)


def is_time_interval_in_schedule(interval_start, interval_end, intervals):
    for start, end in intervals:
        start_time = parse_time(start)
        end_time = parse_time(end)

        if check_overlap(interval_start.time(), interval_end.time(), start_time, end_time):
            return True

    return False


def check_availability_time_range(range_from_now: timedelta):
    # Получаем текущее время в часовом поясе UTC+3
    current_time = datetime.now(pytz.utc)
    current_time = current_time.astimezone(pytz.timezone('Etc/GMT-3'))
    end_time = current_time + range_from_now

    # Проверяем вхождение текущего времени в расписание
    if is_time_interval_in_schedule(current_time, end_time, time_intervals):
        logging.debug("Текущее время входит в расписание.")
        return False
    else:
        logging.debug("Текущее время не входит в расписание.")
        return True


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
        result = int(re.sub(r'[^\d-]', '', trade["result"]))
        if result > 0:
            profit += result
            gross_profit += result
            consecutive_wins += 1
            consecutive_losses = 0
        else:
            loss += abs(result)
            gross_loss += abs(result)
            consecutive_losses += 1
            consecutive_wins = 0

        net_profit += result

        if consecutive_wins > max_consecutive_wins:
            max_consecutive_wins = consecutive_wins

        if consecutive_losses > max_consecutive_losses:
            max_consecutive_losses = consecutive_losses

    avg_profit_trade = gross_profit / total if total > 0 else 0
    avg_loss_trade = gross_loss / total if total > 0 else 0

    data["summary"] = {
        "total": total,
        "profit": profit,
        "loss": loss,
        "refund": refund,
        "net_profit": net_profit,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "avg_profit_trade": avg_profit_trade,
        "avg_loss_trade": avg_loss_trade,
        "max_consecutive_wins": max_consecutive_wins,
        "max_consecutive_losses": max_consecutive_losses
    }

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
    statistic_data = load_statistic_data()

    if additional_data["account_type"] in ["real_dollar", "demo"]:
        money_symbol = "$"
    else:
        money_symbol = "₽"

    info = option_data["info_finish_option"][0]
    # Добавляем новую сделку
    statistic_data["trades"].append(
        {
            "asset": info["symbol"],
            "open_time": convert_datetime_format(info["time_open"]),
            "expiration": get_datetime_difference(info["time_open"], info["time_close"]),
            "close_time": convert_datetime_format(info["time_close"]),
            "open_price": float(info["price_open"]),
            "trade_type": additional_data["trade_type"],
            "close_price": float(info["close_price"]),
            "points": round(float(info["pric"
                                       "e_open"]) - float(info["close_price"]), 3),
            "volume": float(info["sum"]),
            "refund": 0,
            "percentage": int(additional_data["percentage"]),
            "result": f"000{money_symbol}"
        },
    )

    updated_data = recalculate_summary(statistic_data)
    save_statistic_data(updated_data)


if __name__ == "__main__":
    # print(count_expiration_type_1(2))
    print(convert_datetime_format("23 February 06:50:01"))
    # check_availability_time_range(timedelta(hours=6, minutes=36))
