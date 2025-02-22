from datetime import datetime, timedelta

import pytz

from loggingfile import logging


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

if __name__ == "__main__":
    print(count_expiration_type_1(2))
    # check_availability_time_range(timedelta(hours=6, minutes=36))
