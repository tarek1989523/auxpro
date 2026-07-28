import pandas as pd
import ta
import config


class Strategy:

    def _supertrend(self, df, period=10, multiplier=3.0):
        df = df.copy()
        hl2 = (df["high"] + df["low"]) / 2
        atr = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=period)

        up = hl2 - multiplier * atr
        dn = hl2 + multiplier * atr

        st = [0.0] * len(df)
        direction = [1] * len(df)

        for i in range(1, len(df)):
            if df["close"].iloc[i] > dn.iloc[i - 1]:
                direction[i] = 1
            elif df["close"].iloc[i] < up.iloc[i - 1]:
                direction[i] = -1
            else:
                direction[i] = direction[i - 1]
            st[i] = up.iloc[i] if direction[i] == 1 else dn.iloc[i]

        df["st"] = st
        df["st_dir"] = direction
        return df

    def _psar(self, df):
        df = df.copy()
        high = df["high"].values
        low = df["low"].values
        n = len(df)

        af = 0.02
        af_step = 0.02
        af_max = 0.2

        psar = [0.0] * n
        ep = low[0]
        bull = True
        psar[0] = high[0]

        for i in range(1, n):
            if bull:
                psar[i] = psar[i - 1] + af * (ep - psar[i - 1])
                psar[i] = min(psar[i], low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
                if low[i] < psar[i]:
                    bull = False
                    psar[i] = ep
                    ep = low[i]
                    af = af_step
                elif high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
            else:
                psar[i] = psar[i - 1] + af * (ep - psar[i - 1])
                psar[i] = max(psar[i], high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
                if high[i] > psar[i]:
                    bull = True
                    psar[i] = ep
                    ep = high[i]
                    af = af_step
                elif low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)

        df["psar"] = psar
        df["psar_dir"] = [1 if df["close"].iloc[i] > psar[i] else -1 for i in range(n)]
        return df

    def _calc(self, df):
        df = df.copy()
        df["ema5"] = ta.trend.ema_indicator(df["close"], window=5)
        df["ema10"] = ta.trend.ema_indicator(df["close"], window=10)
        df["ema20"] = ta.trend.ema_indicator(df["close"], window=20)
        df["ema50"] = ta.trend.ema_indicator(df["close"], window=50)

        df["macd"] = ta.trend.macd_diff(df["close"])
        df["macd_signal"] = ta.trend.macd_signal(df["close"])
        df["macd_hist"] = ta.trend.macd(df["close"]) - ta.trend.macd_signal(df["close"])

        df["rsi"] = ta.momentum.rsi(df["close"], window=14)
        df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=10)
        df["atr_pips"] = df["atr"] * 10

        df["vol_avg"] = df["tick_volume"].rolling(window=20).mean()
        df["vol_ratio"] = df["tick_volume"] / df["vol_avg"].replace(0, 1)

        df = self._supertrend(df, period=10, multiplier=3.0)
        df = self._psar(df)
        return df

    def _analyze_timeframe(self, df):
        df = self._calc(df)
        c = df.iloc[-1]
        p = df.iloc[-2]

        buy = 0
        sell = 0

        if c["st_dir"] == 1 and p["st_dir"] == -1:
            buy += 4
        elif c["st_dir"] == 1:
            buy += 1

        if c["st_dir"] == -1 and p["st_dir"] == 1:
            sell += 4
        elif c["st_dir"] == -1:
            sell += 1

        if c["psar_dir"] == 1 and p["psar_dir"] == -1:
            buy += 3
        elif c["psar_dir"] == 1:
            buy += 1

        if c["psar_dir"] == -1 and p["psar_dir"] == 1:
            sell += 3
        elif c["psar_dir"] == -1:
            sell += 1

        macd_cross_up = p["macd"] <= p["macd_signal"] and c["macd"] > c["macd_signal"]
        macd_cross_dn = p["macd"] >= p["macd_signal"] and c["macd"] < c["macd_signal"]

        if macd_cross_up:
            buy += 3
        elif c["macd"] > 0 and abs(c["macd"]) > abs(p["macd"]):
            buy += 1

        if macd_cross_dn:
            sell += 3
        elif c["macd"] < 0 and abs(c["macd"]) > abs(p["macd"]):
            sell += 1

        ema_bull = c["ema5"] > c["ema10"] > c["ema20"]
        ema_bear = c["ema5"] < c["ema10"] < c["ema20"]
        ema_cross_up = p["ema5"] <= p["ema10"] and c["ema5"] > c["ema10"]
        ema_cross_dn = p["ema5"] >= p["ema10"] and c["ema5"] < c["ema10"]

        if ema_cross_up:
            buy += 2
        elif ema_bull:
            buy += 2

        if ema_cross_dn:
            sell += 2
        elif ema_bear:
            sell += 2

        return {"buy": buy, "sell": sell, "c": c, "p": p}

    def analyze(self, df_m1, df_m5=None, df_m15=None):
        m1 = self._analyze_timeframe(df_m1)

        trend_buy = 0
        trend_sell = 0

        if df_m5 is not None and len(df_m5) >= 55:
            m5 = self._analyze_timeframe(df_m5)
            trend_buy += m5["buy"]
            trend_sell += m5["sell"]

        if df_m15 is not None and len(df_m15) >= 55:
            m15 = self._analyze_timeframe(df_m15)
            trend_buy += m15["buy"]
            trend_sell += m15["sell"]

        buy_score = m1["buy"] + trend_buy
        sell_score = m1["sell"] + trend_sell

        c = m1["c"]
        p = m1["p"]

        reasons_b = []
        reasons_s = []

        if m1["c"]["st_dir"] == 1 and m1["p"]["st_dir"] == -1:
            reasons_b.append("ST Flip M1")
        if m1["c"]["psar_dir"] == 1 and m1["p"]["psar_dir"] == -1:
            reasons_b.append("PSAR Flip M1")
        if p["macd"] <= p["macd_signal"] and c["macd"] > c["macd_signal"]:
            reasons_b.append("MACD Cross M1")

        if m1["c"]["st_dir"] == -1 and m1["p"]["st_dir"] == 1:
            reasons_s.append("ST Flip M1")
        if m1["c"]["psar_dir"] == -1 and m1["p"]["psar_dir"] == 1:
            reasons_s.append("PSAR Flip M1")
        if p["macd"] >= p["macd_signal"] and c["macd"] < c["macd_signal"]:
            reasons_s.append("MACD Cross M1")

        if trend_buy > 10:
            reasons_b.append("M5+M15 trend UP")
        if trend_sell > 10:
            reasons_s.append("M5+M15 trend DN")

        rsi = c["rsi"]
        at_peak = False
        if rsi > 75:
            at_peak = True
        if rsi < 25:
            at_peak = True

        price = c["close"]
        recent_high = df_m1["high"].iloc[-30:].max()
        recent_low = df_m1["low"].iloc[-30:].min()
        price_range = recent_high - recent_low

        if price_range > 0:
            pos_in_range = (price - recent_low) / price_range
            if pos_in_range > 0.90:
                at_peak = True
            if pos_in_range < 0.10:
                at_peak = True

        signal = "NONE"
        strength = 0
        reasons = []

        if buy_score >= config.MIN_BUY_SCORE and buy_score > sell_score + 1 and not at_peak:
            signal = "BUY"
            strength = buy_score
            reasons = reasons_b
        elif sell_score >= config.MIN_SELL_SCORE and sell_score > buy_score + 1 and not at_peak:
            signal = "SELL"
            strength = sell_score
            reasons = reasons_s

        atr_pips = c["atr_pips"]
        sl_pips = max(atr_pips * 0.8, 15)
        tp_pips = max(atr_pips * 1.5, 25)

        if tp_pips < sl_pips * 1.5:
            tp_pips = sl_pips * 1.5

        return {
            "signal": signal,
            "strength": strength,
            "reasons": reasons,
            "at_peak": at_peak,
            "rsi": round(rsi, 2),
            "price": round(price, 2),
            "st_dir": "UP" if c["st_dir"] == 1 else "DN",
            "psar_dir": "UP" if c["psar_dir"] == 1 else "DN",
            "macd": round(c["macd"], 4),
            "macd_hist": round(c["macd_hist"], 4),
            "ema5": round(c["ema5"], 2),
            "ema10": round(c["ema10"], 2),
            "ema20": round(c["ema20"], 2),
            "atr_pips": round(atr_pips, 2),
            "vol": round(c["vol_ratio"], 2),
            "sl_dist": round(sl_pips * 0.1, 4),
            "tp_dist": round(tp_pips * 0.1, 4),
            "sl_pips": round(sl_pips, 2),
            "tp_pips": round(tp_pips, 2),
            "buy_score": buy_score,
            "sell_score": sell_score,
        }

    def _none(self):
        return {
            "signal": "NONE", "strength": 0, "reasons": [], "at_peak": False,
            "price": 0, "rsi": 0, "macd": 0, "macd_hist": 0,
            "st_dir": "-", "psar_dir": "-",
            "ema5": 0, "ema10": 0, "ema20": 0,
            "atr_pips": 0, "vol": 0,
            "sl_dist": 0, "tp_dist": 0, "sl_pips": 0, "tp_pips": 0,
            "buy_score": 0, "sell_score": 0,
        }
