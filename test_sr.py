import MetaTrader5 as mt5
import pandas as pd
from strategy import Strategy
mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe', login=5053568767, password='QkDeS-N3', server='MetaQuotes-Demo', timeout=60000)
df1 = pd.DataFrame(mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M1, 0, 250)); df1['time'] = pd.to_datetime(df1['time'], unit='s')
df5 = pd.DataFrame(mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M5, 0, 250)); df5['time'] = pd.to_datetime(df5['time'], unit='s')
df15 = pd.DataFrame(mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M15, 0, 250)); df15['time'] = pd.to_datetime(df15['time'], unit='s')
s = Strategy()
a = s.analyze(df1, df5, df15)
print("=== SCALPING STRATEGY ===")
print("Signal:", a['signal'], "| Buy:", a['buy_score'], "| Sell:", a['sell_score'])
print("Price:", a['price'])
print("RSI:", a['rsi'])
print("BB Upper:", a['bb_upper'], "| Lower:", a['bb_lower'], "| Mid:", a['bb_mid'])
print("SuperTrend:", a['st_dir'], "| PSAR:", a['psar_dir'])
print("SL:", a['sl_pips'], "pip | TP:", a['tp_pips'], "pip")
print("Reasons:", a['reasons'])
mt5.shutdown()
