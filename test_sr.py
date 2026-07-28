import MetaTrader5 as mt5
import pandas as pd
from strategy import Strategy
mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe', login=5053568767, password='QkDeS-N3', server='MetaQuotes-Demo', timeout=60000)
df1 = pd.DataFrame(mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M1, 0, 250)); df1['time'] = pd.to_datetime(df1['time'], unit='s')
df5 = pd.DataFrame(mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M5, 0, 250)); df5['time'] = pd.to_datetime(df5['time'], unit='s')
df15 = pd.DataFrame(mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M15, 0, 250)); df15['time'] = pd.to_datetime(df15['time'], unit='s')
s = Strategy()
a = s.analyze(df1, df5, df15)
print('Signal:', a['signal'], '| Buy:', a['buy_score'], '| Sell:', a['sell_score'])
print('At Peak:', a['at_peak'], '| RSI:', a['rsi'])
print('Reasons:', a['reasons'])
sr = s._find_sr_levels(df1, 60)
for lv in sr[:5]:
    t = lv['type']
    p = lv['price']
    st = lv['strength']
    print(f'  {t} @ {p:.2f} x{st}')
mt5.shutdown()
