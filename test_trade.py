import MetaTrader5 as mt5

mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe', login=5053568767, password='QkDeS-N3', server='MetaQuotes-Demo', timeout=60000)

info = mt5.terminal_info()
print(f'AutoTrading: {info.trade_allowed}')

si = mt5.symbol_info('XAUUSD')
print(f'Visible: {si.visible}')
print(f'Spread: {si.spread}')
print(f'Trade allowed: {si.trade_mode}')
print(f'Digits: {si.digits}')
print(f'Point: {si.point}')
print(f'Filling mode: {si.filling_mode}')

bid = mt5.symbol_info_tick('XAUUSD').bid
ask = mt5.symbol_info_tick('XAUUSD').ask
print(f'Bid: {bid} | Ask: {ask}')

result = mt5.order_send({
    'action': mt5.TRADE_ACTION_DEAL,
    'symbol': 'XAUUSD',
    'volume': 0.01,
    'type': mt5.ORDER_TYPE_SELL,
    'price': bid,
    'sl': round(bid + 2.0, 2),
    'tp': round(bid - 2.0, 2),
    'deviation': 10,
    'magic': 202607,
    'type_time': mt5.ORDER_TIME_GTC,
    'type_filling': mt5.ORDER_FILLING_IOC,
})
print(f'Order result: {result.retcode} - {result.comment}')

mt5.shutdown()
