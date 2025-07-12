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
total_loss = []
weekly_loss = []
token = api_keys['token']
chat_id = api_keys["chat_id"]
bot = Bot(token=token)

async def send_summary():
    with open(buyorders, "r") as f:
        data = json.load(f)
        for order in data:
            if "Sold" in order.values() and "date" in order.keys():
                order_date = parser.parse(order['date'])
                if "eur_profit" in order.keys():
                    total_profit.append(order['eur_profit']) 
                    if order_date >= past_week:
                        weekly_profit.append(order['eur_profit'])

                elif "loss" in order.keys():
                    total_loss.append(order["loss"])
                    if order_date >= past_week:
                        weekly_loss.append(order["loss"]
                
    if total_profit and weekly_profit and weekly_loss:
        avg_weekly_profit_per_trade = round(sum(weekly_profit) / len(weekly_profit),2)
        await bot.send_message(chat_id=chat_id, text=f"Weekoverzicht\n\nTotaal inkomsten: €{round(sum(total_profit),2)}\n"
                               f"Inkomsten: €{round(sum(weekly_profit),2)}\n"
                               f"Gemiddelde winst per trade: €{avg_weekly_profit_per_trade}\n"
                               f"Verliezen: €{round(sum(weekly_loss),2)}\n"
                               f"Totaal winst: €{round(sum(total_loss),2)}")

if __name__ == '__main__':
    asyncio.run(send_summary())
