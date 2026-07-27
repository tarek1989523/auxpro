import pandas as pd
import ta
import config


class Strategy:
    def analyze(self, df: pd.DataFrame) -> dict:
        df = df.copy()
        df["ema_f"] = ta.trend.ema_indicator(df["close"], window=config.EMA_FAST)
        df["ema_s"] = ta.trend.ema_indicator(df["close"], window=config.EMA_SLOW)
        df["ema_t"] = ta.trend.ema_indicator(df["close"], window=config.EMA_TREND)
        df["rsi"] = ta.momentum.rsi(df["close"], window=config.RSI_PERIOD)
        df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
        df["macd"] = ta.trend.macd_diff(df["close"])
        df["vol_avg"] = df["tick_volume"].rolling(window=20).mean()
        df["vol_ratio"] = df["tick_volume"] / df["vol_avg"].replace(0, 1)

        if len(df) < config.EMA_TREND + 5:
            return {"signal": "NONE", "strength": 0, "price": 0, "rsi": 0,
                    "atr": 0, "ema_f": 0, "ema_s": 0, "ema_t": 0, "macd": 0}

        c = df.iloc[-1]
        p = df.iloc[-2]

        cross_up = p["ema_f"] <= p["ema_s"] and c["ema_f"] > c["ema_s"]
        above_t = c["close"] > c["ema_t"]
        rsi_b = c["rsi"] < config.RSI_OVERSOLD or (p["rsi"] < 40 and c["rsi"] > p["rsi"])
        vol = c["vol_ratio"] > config.VOLUME_THRESHOLD
        macd_p = c["macd"] > 0

        buy = sum([cross_up * 3, above_t * 2, rsi_b * 2, vol * 1, macd_p * 1])

        cross_dn = p["ema_f"] >= p["ema_s"] and c["ema_f"] < c["ema_s"]
        below_t = c["close"] < c["ema_t"]
        rsi_s = c["rsi"] > config.RSI_OVERBOUGHT or (p["rsi"] > 60 and c["rsi"] < p["rsi"])
        macd_n = c["macd"] < 0

        sell = sum([cross_dn * 3, below_t * 2, rsi_s * 2, vol * 1, macd_n * 1])

        signal = "NONE"
        strength = 0
        if buy >= 7:
            signal, strength = "BUY", buy
        elif sell >= 7:
            signal, strength = "SELL", sell

        atr = c["atr"]
        sl_dist = max(config.STOP_LOSS_PIPS * 0.1, atr * 1.5)
        tp_dist = max(config.TAKE_PROFIT_PIPS * 0.1, atr * 2.0)

        return {
            "signal": signal, "strength": strength,
            "price": round(c["close"], 2), "rsi": round(c["rsi"], 2),
            "atr": round(atr, 4), "ema_f": round(c["ema_f"], 2),
            "ema_s": round(c["ema_s"], 2), "ema_t": round(c["ema_t"], 2),
            "macd": round(c["macd"], 4), "vol": round(c["vol_ratio"], 2),
            "sl_dist": round(sl_dist, 2), "tp_dist": round(tp_dist, 2),
        }
