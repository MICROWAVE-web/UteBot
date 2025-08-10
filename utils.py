from datetime import datetime, timedelta
from typing import List, Tuple

import pytz
from backports.zoneinfo import ZoneInfo

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


def check_unix_interval(point_time_unix: int, intervals: List[tuple]) -> bool:
    """Проверка, попадает ли unix-время в один из заданных интервалов."""
    for start_unix, end_unix in intervals:
        if start_unix < point_time_unix < end_unix:
            return True
    return False


def check_weekend_overlap(point_time: datetime) -> bool:
    """Проверка на выходные (суббота/воскресенье)."""
    return point_time.weekday() in [5, 6]


def check_availability_time_range(serial_start_points: List[timedelta], unix_intervals) -> Tuple[bool, str]:
    """Проверка доступности времени для действия."""

    unix_intervals = [
        (unix_intervals.get(i), unix_intervals.get(i + 1)) for i in range(1, 21, 2)
        if unix_intervals.get(i) and unix_intervals.get(i + 1)
    ]

    current_time = datetime.now(ZoneInfo("Europe/Moscow"))

    for serial_start_point in serial_start_points:
        point_time = current_time + serial_start_point
        point_time_unix = int(point_time.timestamp())

        # Проверка на выходные
        if check_weekend_overlap(point_time):
            return False, "weekend"

        # Проверка на попадание во временные интервалы (из one_percent_time)
        if check_unix_interval(point_time_unix, unix_intervals):
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
        trades = [t for t in data["trades"] if t.get("status") != "pending"]

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
                # Учитываем возвратв 50% как убыточную сделку
                if result < trade['volume']:
                    gross_loss += result
                    loss += 1
                else:
                    refund += 1

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
        return f"{n:.{prec}f}".rstrip('0').rstrip('.')

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

    # Расчитывает result
    if loss_refund:
        result = float(info["finish_current_result_sum"]) - float(info['sum'])
    else:
        result = float(info['finish_current_result_sum'])

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
            "result": f"{round(result, 6)}{money_symbol}",
            "loss_refund": loss_refund,
        },
    )

    save_statistic_data(statistic_data)


def add_pending_option_to_statistic(option_id, pending_data):
    option_id = str(option_id)
    """Добавляет временную запись в статистику."""
    statistic_data = load_statistic_data()

    for sd in statistic_data["trades"]:
        if sd["option_id"] == option_id:
            return False

    # Создаем временную запись
    pending_record = {
        "option_id": option_id,
        "status": "pending",
        **pending_data
    }
    statistic_data["trades"].append(pending_record)
    save_statistic_data(statistic_data)
    return True


def update_option_in_statistic(option_id, real_data):
    option_id = str(option_id)
    """Обновляет временную запись реальными данными."""
    statistic_data = load_statistic_data()

    # Находим и обновляем запись
    for trade in statistic_data["trades"]:
        if trade.get("option_id") == option_id and trade.get("status") == "pending":
            trade.update(real_data)
            trade["status"] = "completed"
            break

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
