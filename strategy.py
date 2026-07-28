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

    def _detect_candles(self, df):
        o = df["open"].values; h = df["high"].values
        l = df["low"].values; c = df["close"].values
        n = len(df)
        body = [abs(c[i] - o[i]) for i in range(n)]
        total_range = [h[i] - l[i] for i in range(n)]
        is_green = [c[i] > o[i] for i in range(n)]
        is_red = [c[i] < o[i] for i in range(n)]

        avg_body = pd.Series(body).rolling(window=20).mean().values

        bullish = [0] * n; bearish = [0] * n
        candle_names = [[] for _ in range(n)]

        for i in range(3, n):
            if total_range[i] == 0:
                continue
            body_ratio = body[i] / total_range[i] if total_range[i] > 0 else 0
            wick_l = (min(o[i], c[i]) - l[i]) / total_range[i] if total_range[i] > 0 else 0
            wick_u = (h[i] - max(o[i], c[i])) / total_range[i] if total_range[i] > 0 else 0

            if wick_l >= 0.6 and body_ratio <= 0.25 and body[i] < avg_body[i]:
                bullish[i] += 2; candle_names[i].append("Hammer")
            if wick_u >= 0.6 and body_ratio <= 0.25 and body[i] < avg_body[i]:
                bearish[i] += 2; candle_names[i].append("Shooting Star")

            if i >= 2:
                if is_red[i-1] and is_green[i]:
                    if abs(c[i]-o[i]) > abs(c[i-1]-o[i-1]) * 1.2:
                        if c[i] > o[i-1] and o[i] < c[i-1]:
                            bullish[i] += 3; candle_names[i].append("Bullish Engulfing")
                if is_green[i-1] and is_red[i]:
                    if abs(c[i]-o[i]) > abs(c[i-1]-o[i-1]) * 1.2:
                        if c[i] < o[i-1] and o[i] > c[i-1]:
                            bearish[i] += 3; candle_names[i].append("Bearish Engulfing")

        df["candle_bull"] = bullish
        df["candle_bear"] = bearish
        df["candle_names"] = candle_names
        return df

    def _calc(self, df):
        df = df.copy()
        df["ema5"] = ta.trend.ema_indicator(df["close"], window=5)
        df["ema20"] = ta.trend.ema_indicator(df["close"], window=20)
        df["ema50"] = ta.trend.ema_indicator(df["close"], window=50)
        df["rsi"] = ta.momentum.rsi(df["close"], window=14)
        df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
        bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_mid"] = bb.bollinger_mavg()
        df["vol_avg"] = df["tick_volume"].rolling(window=20).mean()
        df["vol_ratio"] = df["tick_volume"] / df["vol_avg"].replace(0, 1)
        df = self._supertrend(df, period=10, multiplier=3.0)
        df = self._detect_candles(df)
        return df

    def _find_swing(self, df, lookback=30):
        highs = df["high"].values; lows = df["low"].values; n = len(df)
        high = 0; low = 1e9
        found_h = found_l = False
        for i in range(2, min(lookback, n - 2)):
            idx = n - 1 - i
            if idx < 2 or idx >= n - 2:
                continue
            if highs[idx] > highs[idx-1] and highs[idx] > highs[idx-2] and \
               highs[idx] > highs[idx+1] and highs[idx] > highs[idx+2]:
                if highs[idx] > high:
                    high = highs[idx]; found_h = True
            if lows[idx] < lows[idx-1] and lows[idx] < lows[idx-2] and \
               lows[idx] < lows[idx+1] and lows[idx] < lows[idx+2]:
                if lows[idx] < low:
                    low = lows[idx]; found_l = True
        return (high if found_h else None, low if found_l else None)

    def analyze(self, df_m1, df_m5=None, df_m15=None):
        if df_m1 is None or len(df_m1) < 60:
            return self._none()

        m1 = self._calc(df_m1)
        m5 = self._calc(df_m5) if df_m5 is not None and len(df_m5) >= 60 else None
        m15 = self._calc(df_m15) if df_m15 is not None and len(df_m15) >= 60 else None

        c = m1.iloc[-1]
        p = m1.iloc[-2]

        trend_dir = "NONE"

        if m15 is not None:
            m15c = m15.iloc[-1]
            if m15c["st_dir"] == 1 and m15c["close"] > m15c["ema50"]:
                trend_dir = "UP"
            elif m15c["st_dir"] == -1 and m15c["close"] < m15c["ema50"]:
                trend_dir = "DN"

        if trend_dir == "NONE" and m5 is not None:
            m5c = m5.iloc[-1]
            if m5c["st_dir"] == 1 and m5c["close"] > m5c["ema50"]:
                trend_dir = "UP"
            elif m5c["st_dir"] == -1 and m5c["close"] < m5c["ema50"]:
                trend_dir = "DN"

        buy_score = 0; sell_score = 0
        reasons_b = []; reasons_s = []

        if trend_dir == "UP":
            sell_score -= 3
            buy_score += 3
        elif trend_dir == "DN":
            buy_score -= 3
            sell_score += 3

        if m15 is not None:
            m15c = m15.iloc[-1]; m15p = m15.iloc[-2]
            if m15c["st_dir"] == 1 and m15p["st_dir"] == -1:
                buy_score += 5; reasons_b.append("M15 ST Bullish")
            if m15c["st_dir"] == -1 and m15p["st_dir"] == 1:
                sell_score += 5; reasons_s.append("M15 ST Bearish")
            if m15c["st_dir"] == 1:
                buy_score += 2
            if m15c["st_dir"] == -1:
                sell_score += 2

        if m5 is not None:
            m5c = m5.iloc[-1]; m5p = m5.iloc[-2]
            if m5c["st_dir"] == 1 and m5p["st_dir"] == -1:
                buy_score += 4; reasons_b.append("M5 ST Bullish")
            if m5c["st_dir"] == -1 and m5p["st_dir"] == 1:
                sell_score += 4; reasons_s.append("M5 ST Bearish")
            if m5c["st_dir"] == 1:
                buy_score += 2
            if m5c["st_dir"] == -1:
                sell_score += 2

        st_flip_b = p["st_dir"] == -1 and c["st_dir"] == 1
        st_flip_s = p["st_dir"] == 1 and c["st_dir"] == -1
        if st_flip_b:
            buy_score += 5; reasons_b.append("ST Flip")
        if st_flip_s:
            sell_score += 5; reasons_s.append("ST Flip")
        if c["st_dir"] == 1:
            buy_score += 1
        if c["st_dir"] == -1:
            sell_score += 1

        ema_x_b = p["ema5"] < p["ema20"] and c["ema5"] > c["ema20"]
        ema_x_s = p["ema5"] > p["ema20"] and c["ema5"] < c["ema20"]
        if ema_x_b:
            buy_score += 4; reasons_b.append("EMA Cross")
        if ema_x_s:
            sell_score += 4; reasons_s.append("EMA Cross")
        if c["ema5"] > c["ema20"]:
            buy_score += 1
        if c["ema5"] < c["ema20"]:
            sell_score += 1

        bb_in_up = c["close"] <= c["bb_lower"] + (c["bb_upper"] - c["bb_lower"]) * 0.15
        bb_in_dn = c["close"] >= c["bb_upper"] - (c["bb_upper"] - c["bb_lower"]) * 0.25
        if bb_in_up:
            buy_score += 3; reasons_b.append("BB Low")
        if bb_in_dn:
            sell_score += 3; reasons_s.append("BB High")

        if c["candle_bull"] > 0:
            buy_score += c["candle_bull"]
            if c["candle_names"]:
                reasons_b.append(c["candle_names"][-1][0])
        if c["candle_bear"] > 0:
            sell_score += c["candle_bear"]
            if c["candle_names"]:
                reasons_s.append(c["candle_names"][-1][0])

        if c["vol_ratio"] > 2.0:
            buy_score += 2; sell_score += 2
        elif c["vol_ratio"] > 1.3:
            buy_score += 1; sell_score += 1

        if c["rsi"] < 40:
            buy_score += 2; reasons_b.append(f"RSI {c['rsi']:.0f}")
        elif c["rsi"] < 45:
            buy_score += 1
        if c["rsi"] > 60:
            sell_score += 2; reasons_s.append(f"RSI {c['rsi']:.0f}")
        elif c["rsi"] > 55:
            sell_score += 1

        price = c["close"]
        swing_high, swing_low = self._find_swing(m1)

        atr_val = c["atr"]
        sl_pips_config = config.STOP_LOSS_PIPS
        tp_pips_config = config.TAKE_PROFIT_PIPS

        atr_pips = atr_val / 0.01
        if atr_pips < sl_pips_config * 0.5:
            sl_pips = round(atr_pips * 1.5, 1)
        else:
            sl_pips = float(sl_pips_config)
        tp_pips = round(sl_pips * 2, 1)

        if trend_dir == "UP" and swing_low:
            dyn_sl = round(abs(price - swing_low) / 0.01, 1)
            if 5 < dyn_sl < sl_pips * 2:
                sl_pips = round(max(dyn_sl, 10), 1)
                tp_pips = round(sl_pips * 2, 1)

        if trend_dir == "DN" and swing_high:
            dyn_sl = round(abs(swing_high - price) / 0.01, 1)
            if 5 < dyn_sl < sl_pips * 2:
                sl_pips = round(max(dyn_sl, 10), 1)
                tp_pips = round(sl_pips * 2, 1)

        sl_price_dist = round(sl_pips * 0.01, 2)
        tp_price_dist = round(tp_pips * 0.01, 2)

        min_score = 6
        signal = "NONE"

        if buy_score >= min_score and (st_flip_b or ema_x_b or buy_score >= sell_score + 2):
            signal = "BUY"
        elif sell_score >= min_score and (st_flip_s or ema_x_s or sell_score >= buy_score + 2):
            signal = "SELL"

        reasons = reasons_b if signal == "BUY" else reasons_s
        if trend_dir != "NONE":
            reasons.append(f"Trend: {trend_dir}")

        return {
            "signal": signal,
            "strength": max(buy_score, sell_score),
            "reasons": reasons,
            "price": round(price, 2),
            "st_dir": "UP" if c["st_dir"] == 1 else "DN",
            "rsi": round(c["rsi"], 1),
            "vol": round(c["vol_ratio"], 2),
            "atr_pips": round(atr_pips, 1),
            "sl_dist": sl_price_dist,
            "tp_dist": tp_price_dist,
            "sl_pips": round(sl_pips, 1),
            "tp_pips": round(tp_pips, 1),
            "buy_score": buy_score,
            "sell_score": sell_score,
            "trend": trend_dir,
        }

    def _none(self):
        return {
            "signal": "NONE", "strength": 0, "reasons": [],
            "price": 0, "st_dir": "-", "rsi": 0, "vol": 0,
            "atr_pips": 0, "sl_dist": 0, "tp_dist": 0,
            "sl_pips": 0, "tp_pips": 0,
            "buy_score": 0, "sell_score": 0, "trend": "NONE",
        }
