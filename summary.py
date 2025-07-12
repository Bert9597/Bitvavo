import json
from datetime import datetime, timedelta
from telegram import Bot
import os
from dateutil import parser
import asyncio

now = datetime.now()
past_week = now - timedelta(days=7)  # 7 ipv 8 voor een echte "week"
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
    try:
        with open(buyorders, "r") as f:
            data = json.load(f)
            for order in data:
                if "Sold" in order.values() and "date" in order:
                    order_date = parser.parse(order["date"])

                    if "eur_profit" in order:
                        total_profit.append(order["eur_profit"])
                        if order_date >= past_week:
                            weekly_profit.append(order["eur_profit"])

                    if "loss" in order:
                        total_loss.append(order["loss"])
                        if order_date >= past_week:
                            weekly_loss.append(order["loss"])

        # Bericht opstellen
        if total_profit or total_loss:
            message = "Weekoverzicht\n\n"

            if total_profit:
                message += f"Totaal inkomsten: €{round(sum(total_profit), 2)}\n"

            if weekly_profit:
                message += f"Inkomsten (deze week): €{round(sum(weekly_profit), 2)}\n"
                avg_weekly_profit_per_trade = round(sum(weekly_profit) / len(weekly_profit), 2)
                message += f"Gemiddelde winst per trade: €{avg_weekly_profit_per_trade}\n"

            if weekly_loss:
                message += f"Verliezen (deze week): €{round(sum(weekly_loss), 2)}\n"

            if total_loss:
                if total_profit:
                    message += f"Totaal verlies: €{round(sum(total_loss), 2)}\nWinst:  €{sum(total_profit) - sum(total_loss)}"

                elif not total_profit:
                    message += f"Totaal verlies: €{round(sum(total_loss), 2)}
                    
            await bot.send_message(chat_id=chat_id, text=message)

        else:
            await bot.send_message(chat_id=chat_id, text="Er zijn geen transacties of resultaten om te rapporteren deze week.")

    except Exception as e:
        await bot.send_message(chat_id=chat_id, text=f"⚠️ Fout bij het genereren van rapport: {str(e)}")

if __name__ == '__main__':
    asyncio.run(send_summary())
