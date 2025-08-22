import asyncio
import random

import aiohttp

# список валютных пар
pairs = [
    "EURUSD", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD",
    "GBPUSD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD",
    "AUDUSD", "AUDCAD", "AUDCHF", "AUDJPY",
    "USDCAD", "USDCHF", "USDJPY",
    "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD",
    "CADCHF", "CADJPY", "CHFJPY",
    "BTCUSDT"
]

directs = ["UP", "DOWN"]
url_base = "http://127.0.0.1/"


# отправка одного запроса
async def send_request(session):
    pair = random.choice(pairs)
    direct = random.choice(directs)
    url = f"{url_base}?pair={pair}&direct={direct}"
    try:
        async with session.get(url) as resp:
            text = await resp.text()
            print(f"[{resp.status}] {url} -> {text[:50]}")
    except Exception as e:
        print(f"Ошибка: {e}")


# массовая отправка
async def main():
    tasks = []
    async with aiohttp.ClientSession() as session:
        for _ in range(4):  # число запросов
            tasks.append(send_request(session))
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
