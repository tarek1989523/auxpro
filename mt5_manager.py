from __future__ import annotations
import MetaTrader5 as mt5
import pandas as pd
import logging
import threading
import os
from datetime import datetime
from typing import Optional, List, Dict
import config

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_connected = False


def _find_path() -> Optional[str]:
    paths = [
        config.MT5_PATH,
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def connect(login: int, password: str, server: str) -> bool:
    global _connected
    with _lock:
        if _connected:
            info = mt5.account_info()
            if info and str(info.login) == str(login):
                return True
            try:
                mt5.shutdown()
            except Exception:
                pass
            _connected = False

        path = _find_path()
        try:
            mt5.shutdown()
        except Exception:
            pass

        kw = {"portable": False, "timeout": 60000}
        if path:
            kw["path"] = path

        if not mt5.initialize(**kw):
            logger.error(f"MT5 init failed: {mt5.last_error()}")
            return False

        info = mt5.account_info()
        if info is None:
            logger.error("No account info")
            return False

        if str(info.login) != str(login):
            logger.info(f"Mismatch: need {login}, have {info.login}. Retrying...")
            try:
                mt5.shutdown()
            except Exception:
                pass
            kw2 = {"login": login, "password": password, "server": server,
                    "portable": False, "timeout": 60000}
            if path:
                kw2["path"] = path
            if not mt5.initialize(**kw2):
                logger.info(f"Cannot login as {login}. Reconnecting default...")
                try:
                    mt5.shutdown()
                except Exception:
                    pass
                kw3 = {"portable": False, "timeout": 60000}
                if path:
                    kw3["path"] = path
                if not mt5.initialize(**kw3):
                    return False

        _connected = True
        i = mt5.account_info()
        logger.info(f"Connected: {i.login} ({i.server}) | {i.balance}$")
        return True


def disconnect():
    global _connected
    with _lock:
        try:
            mt5.shutdown()
        except Exception:
            pass
        _connected = False


def account_info() -> Optional[dict]:
    with _lock:
        i = mt5.account_info()
        if not i:
            return None
        return {"login": i.login, "server": i.server, "balance": i.balance,
                "equity": i.equity, "profit": i.profit, "leverage": i.leverage}


def get_positions() -> List[dict]:
    with _lock:
        pos = mt5.positions_get(symbol=config.SYMBOL)
        if not pos:
            return []
        return [{
            "ticket": p.ticket,
            "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
            "volume": p.volume,
            "price_open": p.price_open,
            "price_current": p.price_current,
            "sl": p.sl, "tp": p.tp,
            "profit": p.profit,
            "time": datetime.fromtimestamp(p.time),
        } for p in pos]


def get_ohlcv(tf: str = "M1", count: int = 200) -> Optional[pd.DataFrame]:
    with _lock:
        tf_map = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
                  "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4}
        rates = mt5.copy_rates_from_pos(config.SYMBOL, tf_map.get(tf, mt5.TIMEFRAME_M1), 0, count)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df


def open_order(order_type: str, lot: float, sl: float, tp: float) -> Optional[dict]:
    with _lock:
        si = mt5.symbol_info(config.SYMBOL)
        if si is None:
            return None
        if not si.visible:
            mt5.symbol_select(config.SYMBOL, True)

        price = si.ask if order_type == "BUY" else si.bid
        mt5_type = mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL

        filling = mt5.ORDER_FILLING_IOC
        if si.filling_mode == 1:
            filling = mt5.ORDER_FILLING_FOK
        elif si.filling_mode == 0:
            filling = mt5.ORDER_FILLING_RETURN

        req = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": config.SYMBOL,
            "volume": lot, "type": mt5_type, "price": price,
            "sl": round(sl, si.digits), "tp": round(tp, si.digits),
            "deviation": config.SLIPPAGE, "magic": config.MAGIC_NUMBER,
            "type_time": mt5.ORDER_TIME_GTC, "type_filling": filling,
        }
        res = mt5.order_send(req)
        if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {res}")
            return None
        logger.info(f"Order: {order_type} @ {res.price}")
        return {"ticket": res.order, "price": res.price, "volume": lot}
