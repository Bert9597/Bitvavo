from python_bitvavo_api.bitvavo import Bitvavo
import json
import os
import pandas as pd
import numpy as np
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, Job, CallbackContext, MessageHandler, filters, ContextTypes
import asyncio
import sys
import ta
from datetime import date

api_keys = json.loads(os.getenv('API_KEYS'))
api_key = api_keys['API_KEY']
api_secret = api_keys['API_SECRET']
token = api_keys['token']
chat_id = api_keys["chat_id"]
app = ApplicationBuilder().token(token).build()

bitvavo = Bitvavo({
    'APIKEY': api_keys['API_KEY'],
    'APISECRET': api_keys['API_SECRET'],
    'RESTURL': api_keys['RESTURL'],
    'WSURL': api_keys['WSURL'],

})

class apibot():
    def __init__(self):
        self._bot = None
        self._buy_signals = {}
        self._placesellorders = []
        self._placebuyorder = []
        self._writebuyorder = {}
        self._orders = None
        self._index = 0
        self._chat_id = -4717875969
        self._msg_id = None
        self._file_path = os.getenv("FILE_PATH_BUYORDERS")
        self._operator_id = 426553


    async def timeout_sessie(self, chat_id):
        try:
            await asyncio.sleep(600)  # 15 minuten
            sys.exit()  # Hele programma stoppen
        except asyncio.CancelledError:
            pass


    def maak_knoppen(self):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Ja", callback_data="ja")],
            [InlineKeyboardButton("Neen", callback_data="nee")]
        ])

    async def manage_orders(self, application):
        self._bot = application.bot
        if self._placesellorders:
            await self.place_market_order()

        else:
            pass

        if self._buy_signals and self._index < len(self._buy_signals):
            key, value = list(self._buy_signals.items())[self._index]
            prijs_per_eenheid = value['huidige_marktprijs']
            markt = key

            buy_message = f"Koopsignaal:\nValuta: {markt}\nPrijs per eenheid: €{round(prijs_per_eenheid,2)}\n\n " \
                          f"Totaalbedrag: €{value['orderprijs']}\n" \
                          f"Je hebt €{self.check_balance('EUR')} beschikbaar, wil je deze aankoop bevestigen?"

            await self._bot.send_message(chat_id=self._chat_id, text=buy_message, reply_markup=self.maak_knoppen())
            asyncio.create_task(self.timeout_sessie(self._chat_id))

        elif self._buy_signals and self._index > len(self._buy_signals):
            await self._bot.send_message(chat_id=self._chat_id, text="Er zijn geen koopsignalen meer.")
            sys.exit()

        else:
            sys.exit()

    async def tekst_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        antwoord = update.message.text.lower()
        key, value = list(self._buy_signals.items())[self._index]
        amount = value['hoeveelheid']

        if antwoord == "ja":
            self._placebuyorder = {"market": key, "amount": amount}
            print(self._placebuyorder)
            await self.place_market_order()
            sys.exit()


        if antwoord == "nee":
            self._index += 1
            await self.manage_orders(app)


    async def knop_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        keuze = query.data
        key, value = list(self._buy_signals.items())[self._index]
        amount = value['hoeveelheid']

        if keuze == "ja":
            self._placebuyorder = {"market": key, "amount": amount}
            await self.place_market_order()

            sys.exit()

        elif keuze == "nee":
            self._index += 1
            await self.manage_orders(app)


    async def place_stop_loss(self):
        key, value = list(self._buy_signals.items())[self._index]
        market = key
        amount = value['hoeveelheid']
        stop_loss_price = value['stop_loss']
        stop_loss_limit = value["stop_limit"]

        stop_loss_order = bitvavo.placeOrder(market, 'sell', 'stopLossLimit', {
            'amount': amount,
            'price': stop_loss_limit,
            'triggerType': 'price',
            'stopPrice': stop_loss_price,
            'triggerAmount': stop_loss_price,
            'triggerReference': 'bestBid',
            'operatorId': self._operator_id
        })

        if 'error' in stop_loss_order:
            print(f"Fout bij plaatsen stop-loss order: {stop_loss_order['error']}")
            await self._bot.send_message(chat_id=self._chat_id, text=f"Fout bij het plaatsen van stop-loss order: {stop_loss_order['error']}")

        else:
            print(f"Stop-loss order succesvol geplaatst!")
            await self._bot.send_message(chat_id=self._chat_id,
                                         text=(f"Stop-loss order succesvol geplaatst!"))

            self._writebuyorder["Id"] = stop_loss_order["orderId"]
            if os.path.exists(self._file_path):
                try:
                    with open(self._file_path, 'r') as f:
                        data = json.load(f)
                        if not isinstance(data, list):
                            data = []

                except json.JSONDecodeError:
                    data = []
            else:
                data = []
            data.append(self._writebuyorder)

            with open(self._file_path, 'w') as f:
                json.dump(data, f, indent=4)

            return stop_loss_order


    async def place_market_order(self):
        if self._placesellorders:
            for i in self._placesellorders:
                market = i['market']
                id = i['Id']
                amount = i['amount']
                total_paid = i["total_paid"]
                
                cancel_order = bitvavo.cancelOrder(market, id)
                sell_order = bitvavo.placeOrder(market, "sell", "market", {'amount': amount,  'operatorId': self._operator_id})
                amount_received = float(sell_order["filledAmountQuote"])
                fee_paid = float(sell_order["fills"][0]["fee"])
                total_received = round(amount_received-fee_paid,2)
                profit = round(total_received-total_paid,2)
                
                if 'error' in cancel_order:
                    error_message = f"Fout bij annuleren van stoploss order: {id}"
                    await self._bot.send_message(chat_id=self._chat_id, text=error_message)

                if 'error' in sell_order:
                    error_message = f"Fout bij het verkopen van: {market}\n" \
                                    f"Hoeveelheid: {amount}"
                    await self._bot.send_message(chat_id=self._chat_id, text=error_message)

                else:
                    today = date.today()
                    success_message = f"Verkoop order: {market} succesvol\n" \
                                      f"€{profit} winst!"
                    await self._bot.send_message(chat_id=self._chat_id, text=success_message)

                    if os.path.exists(self._file_path):
                        with open(self._file_path, "r") as f:       
                            data = json.load(f)
            
                        with open(self._file_path, "w") as f:
                            for order in data:
                                if order['Id'] == id:
                                    order['eur_profit'] = profit
                                    order['date'] = str(today)
                                    order['type'] = "Sold"
                                    
                        json.dump(data, f, indent=4)

        if self._placebuyorder:
            market = self._placebuyorder['market']
            amount = self._placebuyorder['amount']
            order = bitvavo.placeOrder(market, 'buy', 'market', {'amount': amount, 'operatorId': self._operator_id})
            fee_paid = float(order["fills"][0]["fee"])
            amount_filled = float(order["filledAmountQuote"])
            total_paid = round(fee_paid+amount_filled,2)
            self._writebuyorder = {"type": "Open", "market": market, "amount": order["fills"][0]["amount"],
                                   "price": order["fills"][0]["price"], "total_paid": total_paid}


            if 'error' in order:
                error_message = f"Fout bij plaatsen koop order: {order['error']}"
                await self._bot.send_message(chat_id=self._chat_id, text=error_message)

            else:
                success_message = "Kooporder succesvol!"
                await self._bot.send_message(chat_id=self._chat_id, text=success_message)
                await self.place_stop_loss()

        else:
            pass

    def get_market_price(self, symbol):
        ticker = bitvavo.tickerPrice({'market': symbol})
        return float(ticker['price']) if 'price' in ticker else None

    def add_indicators(self, df):
        if df is not None:
            df['SMA_50'] = ta.trend.sma_indicator(df['close'], window=50)
            df['SMA_20'] = ta.trend.sma_indicator(df['close'], window=20)
            df['SMA_200'] = ta.trend.sma_indicator(df['close'], window=200)

            df['EMA_8'] = ta.trend.ema_indicator(df['close'], window=8)
            df['EMA_13'] = ta.trend.ema_indicator(df['close'], window=13)
            df['EMA_21'] = ta.trend.ema_indicator(df['close'], window=21)
            df['EMA_55'] = ta.trend.ema_indicator(df['close'], window=55)
            df['EMA_89'] = ta.trend.ema_indicator(df['close'], window=89)

            df['EMA_8_above_EMA_13'] = df['EMA_8'] > df['EMA_13']
            df['EMA_13_above_EMA_21'] = df['EMA_13'] > df['EMA_21']
            df['EMA_21_above_EMA_55'] = df['EMA_21'] > df['EMA_55']
            df['EMA_55_above_EMA_89'] = df['EMA_55'] > df['EMA_89']


            df['EMA_above'] = (df['EMA_8_above_EMA_13'] &
                               df['EMA_13_above_EMA_21'] &
                               df['EMA_21_above_EMA_55'] &
                               df['EMA_55_above_EMA_89'])

            df['EMA_below'] = (~df['EMA_8_above_EMA_13'])

            return df


    def check_balance(self, asset):
        balance = bitvavo.balance({'symbol': asset})
        if 'error' in balance:
            print(f"Fout bij ophalen balans: {balance['error']}")
        else:
            for item in balance:
                if item['symbol'] == asset:
                    available_balance = float(item['available'])

                    return available_balance
        return 0.0


    def get_bitvavo_data(self, market, interval, limit):
        response = bitvavo.candles(market, interval, {'limit': limit})
        if isinstance(response, dict):
            if response['errorCode'] == 205:
                print(f"Aandeel {market} niet gevonden")

                return None
        else:
            data = pd.DataFrame(response, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
            data[['open', 'high', 'low', 'close', 'volume']] = data[
                ['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric)
            data = data.set_index('timestamp')
            data = data.sort_index()
            data['market'] = market

            return data


    def check_orders(self, markets):
        stop_loss_percentage = 5
        take_profit_percentage = 4
        eur_per_trade = 10
        for market in markets:
            current_price = bot.get_market_price(market)
            df = self.get_bitvavo_data(market, '15m', 100)
            df = self.add_indicators(df)
            
            if df is not None:
                last_row = df.iloc[-1]
                if self.check_balance('EUR') and last_row['EMA_above']:
                    quantity = round(eur_per_trade / current_price,3)
                    amount = round(quantity * current_price,2)
                    stop_loss_price = current_price / (1+(stop_loss_percentage/100))
                    take_profit_price = current_price * (1+(take_profit_percentage/100))
                    limit_price = stop_loss_price * 0.99

                    num_decimals_sl = 0 if stop_loss_price >= 1000 else \
                    1 if stop_loss_price >= 1000 < 10000 else \
                    2 if stop_loss_price >= 100 < 1000 else \
                    3 if stop_loss_price >= 10 < 100 else \
                    4 if stop_loss_price >= 1 < 10 else \
                    5 if stop_loss_price < 1 else None

                    num_decimals_tp = 0 if take_profit_price >= 1000 else \
                    1 if take_profit_price >= 1000 < 10000 else \
                    2 if take_profit_price >= 100 < 1000 else \
                    3 if take_profit_price >= 10 < 100 else \
                    4 if take_profit_price >= 1 < 10 else \
                    5 if take_profit_price < 1 else None

                    num_decimals_lp = 0 if limit_price >= 1000 else \
                    1 if limit_price >= 1000 < 10000 else \
                    2 if limit_price >= 100 < 1000 else \
                    3 if limit_price >= 10 < 100 else \
                    4 if limit_price >= 1 < 10 else \
                    5 if limit_price < 1 else None

                    stop_loss_price = round(stop_loss_price, num_decimals_sl)
                    take_profit_price = round(take_profit_price, num_decimals_tp)
                    limit_price = round(limit_price, num_decimals_lp)

                    self._buy_signals[market] = {"hoeveelheid": quantity, "orderprijs": amount,
                    "take_profit": take_profit_price, "stop_loss": stop_loss_price, "stop_limit": limit_price,
                    "huidige_marktprijs": current_price}

            open_orders = bitvavo.ordersOpen({})
            print(open_orders)
            today = date.today()
            if os.path.exists(self._file_path) and self._file_path is not None:
                with open(self._file_path, 'r') as f:
                    data = json.load(f)
                    for order in data:
                        for i in open_orders: 
                            if order['Id'] not in i.values():
                                history = bitvavo.trades(order['market'], {})
                                for x in history:
                                    if order['Id'] == x['orderId']:
                                        fee_paid = x['fee']
                                        received = float(x['amount']) * float(x['price'])
                                        net_received = round(received - fee_paid,2)
                                        timestamp = x['timestamp']
                                        timestamp_s = timestamp / 1000
                                        dt_object = datetime.fromtimestamp(timestamp_s)
                                        date = dt_object.strftime("%Y-%m-%d")
                                        
                                eur_loss = round(net_received - order['total_paid'],2)
                                order['type'] = 'Sold'
                                order['date'] = date
                                order['eur_loss'] = eur_loss
                                
                            elif order['market'] == market and order['Id'] == i['orderId']:
                                profit = round((float(current_price) - float(order['price'])) / float(order['price']) * 100, 2)
                                order['huidige_marktprijs'] = current_price 
                                order['profit_percentage'] = "{}%".format(profit)
                            
                                if last_row['EMA_below'] and profit >= 2:
                                    data = {"market": market, "amount": order["amount"], "Id": order["Id"],
                                            "total_paid": order["total_paid"]}
                                    
                                    bitvavo.cancelOrder(market, order["Id"])
                                    self._placesellorders.append(data)
                                    
                with open (self._file_path, 'w') as f:
                    json.dump(data, f, indent=4)
                    
                                    
if __name__ == '__main__':
    bot = apibot()
    bot.check_orders(['RED-EUR', 'MKR-EUR', 'ICP-EUR'])
    app.add_handler(CallbackQueryHandler(bot.knop_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.tekst_handler))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.manage_orders(app))
    app.run_polling()
