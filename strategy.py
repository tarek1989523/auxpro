import pandas as pd
import ta
import config


class Strategy:
    def _calc(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df["ema8"] = ta.trend.ema_indicator(df["close"], window=8)
        df["ema21"] = ta.trend.ema_indicator(df["close"], window=21)
        df["ema50"] = ta.trend.ema_indicator(df["close"], window=50)
        df["ema200"] = ta.trend.ema_indicator(df["close"], window=200)

        df["rsi"] = ta.momentum.rsi(df["close"], window=14)
        df["rsi_6"] = ta.momentum.rsi(df["close"], window=6)

        df["macd"] = ta.trend.macd_diff(df["close"])
        df["macd_signal"] = ta.trend.macd_signal(df["close"])

        df["stoch_k"] = ta.momentum.stoch(df["high"], df["low"], df["close"], window=14, smooth_window=3)
        df["stoch_d"] = ta.momentum.stoch_signal(df["high"], df["low"], df["close"], window=14, smooth_window=3)

        df["bb_upper"] = ta.volatility.bollinger_hband(df["close"], window=20, window_dev=2)
        df["bb_lower"] = ta.volatility.bollinger_lband(df["close"], window=20, window_dev=2)
        df["bb_mid"] = ta.volatility.bollinger_mavg(df["close"], window=20)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

        df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)

        df["adx"] = ta.trend.adx(df["high"], df["low"], df["close"], window=14)
        df["di_plus"] = ta.trend.adx_pos(df["high"], df["low"], df["close"], window=14)
        df["di_minus"] = ta.trend.adx_neg(df["high"], df["low"], df["close"], window=14)

        df["vol_avg"] = df["tick_volume"].rolling(window=20).mean()
        df["vol_ratio"] = df["tick_volume"] / df["vol_avg"].replace(0, 1)

        df["atr_pips"] = df["atr"] * 10

        return df

    def analyze(self, df: pd.DataFrame) -> dict:
        df = self._calc(df)
        if len(df) < 205:
            return self._none()

        c = df.iloc[-1]
        p = df.iloc[-2]
        p2 = df.iloc[-3]

        buy_score = 0
        sell_score = 0
        reasons_b = []
        reasons_s = []

        # --- Trend (M15 context via EMAs) ---
        above_ema50 = c["close"] > c["ema50"]
        above_ema200 = c["close"] > c["ema200"]
        below_ema50 = c["close"] < c["ema50"]
        below_ema200 = c["close"] < c["ema200"]

        if above_ema50:
            buy_score += 1
            reasons_b.append("Above EMA50")
        if above_ema200:
            buy_score += 1
            reasons_b.append("Above EMA200")
        if below_ema50:
            sell_score += 1
            reasons_s.append("Below EMA50")
        if below_ema200:
            sell_score += 1
            reasons_s.append("Below EMA200")

        # --- EMA Crossover (M5 signal) ---
        cross_up = p["ema8"] <= p["ema21"] and c["ema8"] > c["ema21"]
        cross_dn = p["ema8"] >= p["ema21"] and c["ema8"] < c["ema21"]
        ema_bull = c["ema8"] > c["ema21"] and c["ema21"] > c["ema50"]
        ema_bear = c["ema8"] < c["ema21"] and c["ema21"] < c["ema50"]

        if cross_up:
            buy_score += 3
            reasons_b.append("EMA Cross UP")
        elif ema_bull:
            buy_score += 1

        if cross_dn:
            sell_score += 3
            reasons_s.append("EMA Cross DN")
        elif ema_bear:
            sell_score += 1

        # --- MACD ---
        macd_cross_up = p["macd"] <= p["macd_signal"] and c["macd"] > c["macd_signal"]
        macd_cross_dn = p["macd"] >= p["macd_signal"] and c["macd"] < c["macd_signal"]
        macd_positive = c["macd"] > 0
        macd_negative = c["macd"] < 0

        if macd_cross_up:
            buy_score += 2
            reasons_b.append("MACD Cross UP")
        elif macd_positive:
            buy_score += 1

        if macd_cross_dn:
            sell_score += 2
            reasons_s.append("MACD Cross DN")
        elif macd_negative:
            sell_score += 1

        # --- RSI ---
        rsi_buy = c["rsi"] < 35 or (p["rsi"] < 40 and c["rsi"] > p["rsi"])
        rsi_sell = c["rsi"] > 65 or (p["rsi"] > 60 and c["rsi"] < p["rsi"])
        rsi_momentum_up = c["rsi"] > p["rsi"] > p2["rsi"]
        rsi_momentum_dn = c["rsi"] < p["rsi"] < p2["rsi"]

        if rsi_buy:
            buy_score += 2
            reasons_b.append(f"RSI={c['rsi']:.0f}")
        if rsi_momentum_up:
            buy_score += 1

        if rsi_sell:
            sell_score += 2
            reasons_s.append(f"RSI={c['rsi']:.0f}")
        if rsi_momentum_dn:
            sell_score += 1

        # --- Stochastic ---
        stoch_buy = c["stoch_k"] < 25 and c["stoch_k"] > c["stoch_d"]
        stoch_sell = c["stoch_k"] > 75 and c["stoch_k"] < c["stoch_d"]
        stoch_cross_up = p["stoch_k"] <= p["stoch_d"] and c["stoch_k"] > c["stoch_d"]
        stoch_cross_dn = p["stoch_k"] >= p["stoch_d"] and c["stoch_k"] < c["stoch_d"]

        if stoch_cross_up:
            buy_score += 2
            reasons_b.append("Stoch Cross UP")
        elif stoch_buy:
            buy_score += 1

        if stoch_cross_dn:
            sell_score += 2
            reasons_s.append("Stoch Cross DN")
        elif stoch_sell:
            sell_score += 1

        # --- Bollinger Bands ---
        bb_squeeze = c["bb_width"] < df["bb_width"].rolling(20).mean().iloc[-1]
        bb_touch_lower = c["close"] <= c["bb_lower"] * 1.001
        bb_touch_upper = c["close"] >= c["bb_upper"] * 0.999

        if bb_touch_lower:
            buy_score += 2
            reasons_b.append("BB Lower Touch")
        if bb_touch_upper:
            sell_score += 2
            reasons_s.append("BB Upper Touch")

        # --- ADX Trend Strength ---
        adx_strong = c["adx"] > 20
        di_bull = c["di_plus"] > c["di_minus"]
        di_bear = c["di_minus"] > c["di_plus"]

        if adx_strong and di_bull:
            buy_score += 1
            reasons_b.append(f"ADX={c['adx']:.0f}")
        if adx_strong and di_bear:
            sell_score += 1
            reasons_s.append(f"ADX={c['adx']:.0f}")

        # --- Volume ---
        vol_spike = c["vol_ratio"] > 1.5
        vol_ok = c["vol_ratio"] > config.VOLUME_THRESHOLD

        if vol_spike:
            buy_score += 1
            sell_score += 1
        if vol_ok:
            buy_score += 1
            sell_score += 1

        # --- Decision ---
        signal = "NONE"
        strength = 0
        reasons = []

        min_score = 10

        if buy_score >= min_score and buy_score > sell_score + 2:
            signal = "BUY"
            strength = buy_score
            reasons = reasons_b
        elif sell_score >= min_score and sell_score > buy_score + 2:
            signal = "SELL"
            strength = sell_score
            reasons = reasons_s

        # --- Dynamic SL/TP ---
        atr = c["atr"]
        atr_pips = c["atr_pips"]

        sl_pips = max(atr_pips * 1.5, config.STOP_LOSS_PIPS * 0.1)
        tp_pips = max(atr_pips * 2.5, config.TAKE_PROFIT_PIPS * 0.1)

        # Better risk:reward - at least 1:2
        if tp_pips < sl_pips * 2:
            tp_pips = sl_pips * 2

        sl_dist = sl_pips * 0.1
        tp_dist = tp_pips * 0.1

        return {
            "signal": signal,
            "strength": strength,
            "reasons": reasons,
            "price": round(c["close"], 2),
            "rsi": round(c["rsi"], 2),
            "rsi_6": round(c["rsi_6"], 2),
            "stoch_k": round(c["stoch_k"], 2),
            "stoch_d": round(c["stoch_d"], 2),
            "atr": round(atr, 4),
            "atr_pips": round(atr_pips, 2),
            "ema8": round(c["ema8"], 2),
            "ema21": round(c["ema21"], 2),
            "ema50": round(c["ema50"], 2),
            "ema200": round(c["ema200"], 2),
            "macd": round(c["macd"], 4),
            "adx": round(c["adx"], 2),
            "bb_width": round(c["bb_width"], 6),
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
            "price": 0, "rsi": 0, "rsi_6": 0,
            "stoch_k": 0, "stoch_d": 0,
            "atr": 0, "atr_pips": 0,
            "ema8": 0, "ema21": 0, "ema50": 0, "ema200": 0,
            "macd": 0, "adx": 0, "bb_width": 0, "vol": 0,
            "sl_dist": 0, "tp_dist": 0, "sl_pips": 0, "tp_pips": 0,
            "buy_score": 0, "sell_score": 0,
        }
