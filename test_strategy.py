import MetaTrader5 as mt5
import pandas as pd
import sys
sys.path.insert(0, '.')
from strategy import Strategy
from news import fetch_forex_factory, is_high_impact_now, fetch_gold_news, get_market_sentiment
import config

mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe', login=5053568767, password='QkDeS-N3', server='MetaQuotes-Demo', timeout=60000)

rates = mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M1, 0, 250)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

s = Strategy()
a = s.analyze(df)
print('Signal:', a['signal'])
print('Buy:', a['buy_score'], '| Sell:', a['sell_score'])
print('Strength:', a['strength'])
print('Reasons:', a['reasons'])
print('SuperTrend:', a['st_dir'])
print('PSAR:', a['psar_dir'])
print('MACD:', a['macd'])
print('RSI:', a['rsi'])
print('Volume:', a['vol'])

events = fetch_forex_factory()
high_impact = is_high_impact_now(events)
print('High impact news:', high_impact)

news = fetch_gold_news()
sentiment = get_market_sentiment(news)
print('Market sentiment:', sentiment['label'], sentiment['emoji'])

mt5.shutdown()
