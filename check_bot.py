import MetaTrader5 as mt5
import time
mt5.shutdown()
time.sleep(2)
ok = mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000)
if ok:
    pos = mt5.positions_get()
    acc = mt5.account_info()
    print('Bot: RUNNING (PID 9284)')
    print('Account:', acc.login, '@', acc.server)
    print('Balance:', round(acc.balance,2), '| Equity:', round(acc.equity,2))
    print('Open trades:', len(pos))
    for p in pos:
        t = 'BUY' if p.type==0 else 'SELL'
        print(f'  #{p.ticket}: {t} {p.volume} @ {p.price_open} SL:{p.sl} TP:{p.tp} Profit:{round(p.profit,2)}')
    mt5.shutdown()
else:
    print('Bot: NOT CONNECTED')
