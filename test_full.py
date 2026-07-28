import asyncio
import sys
sys.path.insert(0, '.')
import config
from strategy import Strategy
from news import fetch_forex_factory, is_high_impact_now
import MetaTrader5 as mt5
import pandas as pd

s = Strategy()

events = fetch_forex_factory()
high_impact = is_high_impact_now(events)
print(f'High impact news blocking: {high_impact}')

info = mt5.account_info()
print(f'MT5 connected: {info is not None}')

if not info:
    mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe', login=5053568767, password='QkDeS-N3', server='MetaQuotes-Demo', timeout=60000)

df1 = mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M1, 0, 250)
df5 = mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M5, 0, 250)
df15 = mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M15, 0, 250)

df1 = pd.DataFrame(df1); df1['time'] = pd.to_datetime(df1['time'], unit='s')
df5 = pd.DataFrame(df5); df5['time'] = pd.to_datetime(df5['time'], unit='s')
df15 = pd.DataFrame(df15); df15['time'] = pd.to_datetime(df15['time'], unit='s')

a = s.analyze(df1, df5, df15)
print(f'Signal: {a["signal"]}')
print(f'Buy: {a["buy_score"]} | Sell: {a["sell_score"]}')
print(f'Min: {config.MIN_BUY_SCORE}')
print(f'Trend: {a.get("trend")}')

pos = mt5.positions_get()
print(f'Positions: {len(pos) if pos else 0}')

if a["signal"] in ("BUY", "SELL"):
    sig = a["signal"]
    price = a["price"]
    sl = price - a["sl_dist"] if sig == "BUY" else price + a["sl_dist"]
    tp = price + a["tp_dist"] if sig == "BUY" else price - a["tp_dist"]
    print(f'Would open: {sig} @ {price} SL={sl:.2f} TP={tp:.2f}')
    
    si = mt5.symbol_info('XAUUSD')
    tick = mt5.symbol_info_tick('XAUUSD')
    p = tick.bid if sig == "SELL" else tick.ask
    mt5_type = mt5.ORDER_TYPE_SELL if sig == "SELL" else mt5.ORDER_TYPE_BUY
    filling = mt5.ORDER_FILLING_IOC
    if si.filling_mode == 1: filling = mt5.ORDER_FILLING_FOK
    elif si.filling_mode == 0: filling = mt5.ORDER_FILLING_RETURN
    
    result = mt5.order_send({
        'action': mt5.TRADE_ACTION_DEAL, 'symbol': 'XAUUSD',
        'volume': 0.01, 'type': mt5_type, 'price': p,
        'sl': round(sl, si.digits), 'tp': round(tp, si.digits),
        'deviation': 10, 'magic': 202607,
        'type_time': mt5.ORDER_TIME_GTC, 'type_filling': filling,
    })
    print(f'Order: {result.retcode} - {result.comment}')

mt5.shutdown()
