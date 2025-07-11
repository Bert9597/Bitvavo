import json
from datetime import datetime, timedelta
from telegram import Bot
import os
from dateutil import parser
import asyncio

now = datetime.now()
past_week = now-timedelta(days=8)
buyorders = os.getenv("FILE_PATH_BUYORDERS")
api_keys = json.loads(os.getenv('API_KEYS'))
weekly_profit = []
total_profit = []
token = api_keys['token']
chat_id = api_keys["chat_id"]
bot = Bot(token=token)

async def send_summary():
    with open(buyorders, "r") as f:
        data = json.load(f)
        for order in data:
            if "Sold" in order.values() and "date" in order.keys() and "eur_profit" in order.keys():
                order_date = parser.parse(order['date'])
                if order_date >= past_week:
                    weekly_profit.append(order['eur_profit'])
                    
                total_profit.append(order['eur_profit']) 
            
    if total_profit and weekly_profit:
        avg_weekly_profit_per_trade = round(total_weekly_profit / len(weekly_profit),2)
        await bot.send_message(chat_id=chat_id, text=f"Weekoverzicht\n\nTotaal inkomsten: €{round(sum(total_profit),2)}\n"
                               f"Inkomsten: €{total_weekly_profit}\n"
                               f"Gemmidelde winst per trade: €{avg_weekly_profit_per_trade}"))

if __name__ == '__main__':
    asyncio.run(send_summary())
