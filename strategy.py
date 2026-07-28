import pandas as pd
import ta
import config
import numpy as np


class Strategy:
    def _supertrend(self, df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
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

            if direction[i] == 1:
                st[i] = up.iloc[i]
            else:
                st[i] = dn.iloc[i]

        df["st"] = st
        df["st_dir"] = direction
        return df

    def _psar(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
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
                else:
                    if high[i] > ep:
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
                else:
                    if low[i] < ep:
                        ep = low[i]
                        af = min(af + af_step, af_max)

            if bull:
                direction = 1
            else:
                direction = -1

        df["psar"] = psar
        df["psar_dir"] = [1 if df["close"].iloc[i] > psar[i] else -1 for i in range(n)]
        return df

    def _calc(self, df: pd.DataFrame) -> pd.DataFrame:
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

    def analyze(self, df: pd.DataFrame) -> dict:
        df = self._calc(df)
        if len(df) < 55:
            return self._none()

        c = df.iloc[-1]
        p = df.iloc[-2]
        p2 = df.iloc[-3]

        buy_score = 0
        sell_score = 0
        reasons_b = []
        reasons_s = []

        # --- 1. SuperTrend ---
        if c["st_dir"] == 1 and p["st_dir"] == -1:
            buy_score += 3
            reasons_b.append("ST Flip UP")
        elif c["st_dir"] == 1:
            buy_score += 1

        if c["st_dir"] == -1 and p["st_dir"] == 1:
            sell_score += 3
            reasons_s.append("ST Flip DN")
        elif c["st_dir"] == -1:
            sell_score += 1

        # --- 2. Parabolic SAR ---
        if c["psar_dir"] == 1 and p["psar_dir"] == -1:
            buy_score += 3
            reasons_b.append("PSAR Flip UP")
        elif c["psar_dir"] == 1:
            buy_score += 1

        if c["psar_dir"] == -1 and p["psar_dir"] == 1:
            sell_score += 3
            reasons_s.append("PSAR Flip DN")
        elif c["psar_dir"] == -1:
            sell_score += 1

        # --- 3. MACD ---
        macd_cross_up = p["macd"] <= p["macd_signal"] and c["macd"] > c["macd_signal"]
        macd_cross_dn = p["macd"] >= p["macd_signal"] and c["macd"] < c["macd_signal"]
        hist_growing = abs(c["macd"]) > abs(p["macd"])

        if macd_cross_up:
            buy_score += 3
            reasons_b.append("MACD Cross UP")
        elif c["macd"] > 0 and hist_growing:
            buy_score += 1

        if macd_cross_dn:
            sell_score += 3
            reasons_s.append("MACD Cross DN")
        elif c["macd"] < 0 and hist_growing:
            sell_score += 1

        # --- 4. EMA Trend ---
        ema_bull = c["ema5"] > c["ema10"] > c["ema20"]
        ema_bear = c["ema5"] < c["ema10"] < c["ema20"]
        ema_cross_up = p["ema5"] <= p["ema10"] and c["ema5"] > c["ema10"]
        ema_cross_dn = p["ema5"] >= p["ema10"] and c["ema5"] < c["ema10"]

        if ema_cross_up:
            buy_score += 2
            reasons_b.append("EMA Cross UP")
        elif ema_bull:
            buy_score += 2
            reasons_b.append("EMA Aligned")

        if ema_cross_dn:
            sell_score += 2
            reasons_s.append("EMA Cross DN")
        elif ema_bear:
            sell_score += 2
            reasons_s.append("EMA Aligned")

        # --- 5. Volume ---
        vol_spike = c["vol_ratio"] > 1.5
        vol_ok = c["vol_ratio"] > config.VOLUME_THRESHOLD

        if vol_spike:
            buy_score += 2
            sell_score += 2
            reasons_b.append(f"Vol Spike {c['vol_ratio']:.1f}x")
            reasons_s.append(f"Vol Spike {c['vol_ratio']:.1f}x")
        elif vol_ok:
            buy_score += 1
            sell_score += 1

        # --- 6. RSI confirmation ---
        if c["rsi"] < 40 and c["rsi"] > p["rsi"]:
            buy_score += 1
            reasons_b.append(f"RSI={c['rsi']:.0f}")
        if c["rsi"] > 60 and c["rsi"] < p["rsi"]:
            sell_score += 1
            reasons_s.append(f"RSI={c['rsi']:.0f}")

        # --- Decision ---
        signal = "NONE"
        strength = 0
        reasons = []

        if buy_score >= config.MIN_BUY_SCORE and buy_score > sell_score + 1:
            signal = "BUY"
            strength = buy_score
            reasons = reasons_b
        elif sell_score >= config.MIN_SELL_SCORE and sell_score > buy_score + 1:
            signal = "SELL"
            strength = sell_score
            reasons = reasons_s

        # --- Dynamic SL/TP (tight for scalping) ---
        atr = c["atr"]
        atr_pips = c["atr_pips"]

        sl_pips = max(atr_pips * 1.0, 20)
        tp_pips = max(atr_pips * 1.5, 30)

        if tp_pips < sl_pips * 1.5:
            tp_pips = sl_pips * 1.5

        sl_dist = sl_pips * 0.1
        tp_dist = tp_pips * 0.1

        return {
            "signal": signal,
            "strength": strength,
            "reasons": reasons,
            "price": round(c["close"], 2),
            "rsi": round(c["rsi"], 2),
            "macd": round(c["macd"], 4),
            "macd_hist": round(c["macd_hist"], 4),
            "st_dir": "UP" if c["st_dir"] == 1 else "DN",
            "psar_dir": "UP" if c["psar_dir"] == 1 else "DN",
            "ema5": round(c["ema5"], 2),
            "ema10": round(c["ema10"], 2),
            "ema20": round(c["ema20"], 2),
            "atr": round(atr, 4),
            "atr_pips": round(atr_pips, 2),
            "vol": round(c["vol_ratio"], 2),
            "sl_dist": round(sl_dist, 2),
            "tp_dist": round(tp_dist, 2),
            "sl_pips": round(sl_pips, 2),
            "tp_pips": round(tp_pips, 2),
            "buy_score": buy_score,
            "sell_score": sell_score,
        }

    def _none(self):
        return {
            "signal": "NONE", "strength": 0, "reasons": [],
            "price": 0, "rsi": 0, "macd": 0, "macd_hist": 0,
            "st_dir": "-", "psar_dir": "-",
            "ema5": 0, "ema10": 0, "ema20": 0,
            "atr": 0, "atr_pips": 0, "vol": 0,
            "sl_dist": 0, "tp_dist": 0, "sl_pips": 0, "tp_pips": 0,
            "buy_score": 0, "sell_score": 0,
        }
