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
        af = 0.02; af_step = 0.02; af_max = 0.2
        psar = [0.0] * n
        ep = low[0]; bull = True; psar[0] = high[0]
        for i in range(1, n):
            if bull:
                psar[i] = psar[i - 1] + af * (ep - psar[i - 1])
                psar[i] = min(psar[i], low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
                if low[i] < psar[i]:
                    bull = False; psar[i] = ep; ep = low[i]; af = af_step
                elif high[i] > ep:
                    ep = high[i]; af = min(af + af_step, af_max)
            else:
                psar[i] = psar[i - 1] + af * (ep - psar[i - 1])
                psar[i] = max(psar[i], high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
                if high[i] > psar[i]:
                    bull = True; psar[i] = ep; ep = high[i]; af = af_step
                elif low[i] < ep:
                    ep = low[i]; af = min(af + af_step, af_max)
        df["psar"] = psar
        df["psar_dir"] = [1 if df["close"].iloc[i] > psar[i] else -1 for i in range(n)]
        return df

    def _detect_candles(self, df):
        o = df["open"].values; h = df["high"].values
        l = df["low"].values; c = df["close"].values
        n = len(df)
        body = [abs(c[i] - o[i]) for i in range(n)]
        total_range = [h[i] - l[i] for i in range(n)]
        upper_wick = [h[i] - max(o[i], c[i]) for i in range(n)]
        lower_wick = [min(o[i], c[i]) - l[i] for i in range(n)]
        is_green = [c[i] > o[i] for i in range(n)]
        is_red = [c[i] < o[i] for i in range(n)]

        avg_body = pd.Series(body).rolling(window=20).mean().values
        avg_range = pd.Series(total_range).rolling(window=20).mean().values

        bullish = [0] * n; bearish = [0] * n
        candle_names = [[] for _ in range(n)]

        for i in range(3, n):
            if avg_range[i] == 0 or avg_body[i] == 0:
                continue
            body_ratio = body[i] / total_range[i] if total_range[i] > 0 else 0
            wick_l = lower_wick[i] / total_range[i] if total_range[i] > 0 else 0
            wick_u = upper_wick[i] / total_range[i] if total_range[i] > 0 else 0

            if wick_l >= 0.6 and body_ratio <= 0.25 and body[i] < avg_body[i]:
                bullish[i] += 2; candle_names[i].append("Hammer")
            if wick_u >= 0.6 and body_ratio <= 0.25 and body[i] < avg_body[i]:
                bearish[i] += 2; candle_names[i].append("Shooting Star")
            if body[i] < avg_body[i] * 0.15 and total_range[i] > avg_range[i] * 0.3:
                candle_names[i].append("Doji")

            if i >= 2:
                if is_red[i-1] and is_green[i]:
                    if abs(c[i]-o[i]) > abs(c[i-1]-o[i-1]) * 1.2:
                        if c[i] > o[i-1] and o[i] < c[i-1]:
                            bullish[i] += 3; candle_names[i].append("Bullish Engulfing")
                if is_green[i-1] and is_red[i]:
                    if abs(c[i]-o[i]) > abs(c[i-1]-o[i-1]) * 1.2:
                        if c[i] < o[i-1] and o[i] > c[i-1]:
                            bearish[i] += 3; candle_names[i].append("Bearish Engulfing")

            if i >= 2:
                if is_red[i-2] and is_green[i]:
                    b2 = abs(c[i-2]-o[i-2]); b1 = abs(c[i-1]-o[i-1]); b0 = abs(c[i]-o[i])
                    if b1 < b2*0.3 and b0 > b2*0.5 and c[i] > (o[i-2]+c[i-2])/2:
                        bullish[i] += 4; candle_names[i].append("Morning Star")
                if is_green[i-2] and is_red[i]:
                    b2 = abs(c[i-2]-o[i-2]); b1 = abs(c[i-1]-o[i-1]); b0 = abs(c[i]-o[i])
                    if b1 < b2*0.3 and b0 > b2*0.5 and c[i] < (o[i-2]+c[i-2])/2:
                        bearish[i] += 4; candle_names[i].append("Evening Star")

            if i >= 2:
                if all(is_green[i-j] for j in range(3)):
                    if all(abs(c[i-j]-o[i-j]) > avg_body[i]*0.5 for j in range(3)):
                        if c[i] > c[i-1] > c[i-2]:
                            bullish[i] += 3; candle_names[i].append("3 White Soldiers")
                if all(is_red[i-j] for j in range(3)):
                    if all(abs(c[i-j]-o[i-j]) > avg_body[i]*0.5 for j in range(3)):
                        if c[i] < c[i-1] < c[i-2]:
                            bearish[i] += 3; candle_names[i].append("3 Black Crows")

            if i >= 2:
                if is_green[i-1] and is_red[i]:
                    if body[i-1] > avg_body[i]*0.8 and body[i] > avg_body[i]*0.8:
                        if c[i] < o[i-1] and o[i] > c[i-1]:
                            bearish[i] += 3; candle_names[i].append("Tweezers Top")
                if is_red[i-1] and is_green[i]:
                    if body[i-1] > avg_body[i]*0.8 and body[i] > avg_body[i]*0.8:
                        if c[i] > o[i-1] and o[i] < c[i-1]:
                            bullish[i] += 3; candle_names[i].append("Tweezers Bottom")

        df["candle_bull"] = bullish
        df["candle_bear"] = bearish
        df["candle_names"] = candle_names
        return df

    def _calc(self, df):
        df = df.copy()
        df["ema5"] = ta.trend.ema_indicator(df["close"], window=5)
        df["ema10"] = ta.trend.ema_indicator(df["close"], window=10)
        df["ema20"] = ta.trend.ema_indicator(df["close"], window=20)
        df["macd"] = ta.trend.macd_diff(df["close"])
        df["macd_signal"] = ta.trend.macd_signal(df["close"])
        df["rsi"] = ta.momentum.rsi(df["close"], window=14)
        df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=10)
        df["atr_pips"] = df["atr"] * 10
        bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_mid"] = bb.bollinger_mavg()
        df["vol_avg"] = df["tick_volume"].rolling(window=20).mean()
        df["vol_ratio"] = df["tick_volume"] / df["vol_avg"].replace(0, 1)
        df = self._supertrend(df, period=10, multiplier=3.0)
        df = self._psar(df)
        df = self._detect_candles(df)
        return df

    def _find_sr(self, df, lookback=60):
        levels = []
        highs = df["high"].values; lows = df["low"].values; n = len(df)
        for i in range(3, min(lookback, n - 3)):
            idx = n - 1 - i
            if idx < 3 or idx >= n - 3: continue
            if highs[idx] > highs[idx-1] and highs[idx] > highs[idx-2] and \
               highs[idx] > highs[idx+1] and highs[idx] > highs[idx+2]:
                levels.append({"price": highs[idx], "type": "resistance", "hits": 1})
            if lows[idx] < lows[idx-1] and lows[idx] < lows[idx-2] and \
               lows[idx] < lows[idx+1] and lows[idx] < lows[idx+2]:
                levels.append({"price": lows[idx], "type": "support", "hits": 1})
        merged = []; tol = 0.003
        for lv in levels:
            found = False
            for m in merged:
                if abs(lv["price"] - m["price"]) / m["price"] < tol:
                    m["hits"] += 1; found = True; break
            if not found: merged.append(lv.copy())
        return sorted(merged, key=lambda x: x["hits"], reverse=True)[:10]

    def _near_sr(self, price, levels, atr_pips):
        zone = atr_pips * 0.5
        near_sup = near_res = False; sup_px = res_px = 0
        for lv in levels:
            dist = abs(price - lv["price"]) / 0.01
            if dist > zone: continue
            if lv["type"] == "support": near_sup = True; sup_px = lv["price"]
            if lv["type"] == "resistance": near_res = True; res_px = lv["price"]
        return near_sup, near_res, sup_px, res_px

    def _analyze_tf(self, df):
        df = self._calc(df)
        c = df.iloc[-1]; p = df.iloc[-2]
        buy = 0; sell = 0

        if c["st_dir"] == 1 and p["st_dir"] == -1: buy += 4
        elif c["st_dir"] == 1: buy += 1
        if c["st_dir"] == -1 and p["st_dir"] == 1: sell += 4
        elif c["st_dir"] == -1: sell += 1

        if c["psar_dir"] == 1 and p["psar_dir"] == -1: buy += 3
        elif c["psar_dir"] == 1: buy += 1
        if c["psar_dir"] == -1 and p["psar_dir"] == 1: sell += 3
        elif c["psar_dir"] == -1: sell += 1

        if p["macd"] <= p["macd_signal"] and c["macd"] > c["macd_signal"]: buy += 3
        elif c["macd"] > 0 and abs(c["macd"]) > abs(p["macd"]): buy += 1
        if p["macd"] >= p["macd_signal"] and c["macd"] < c["macd_signal"]: sell += 3
        elif c["macd"] < 0 and abs(c["macd"]) > abs(p["macd"]): sell += 1

        if p["ema5"] <= p["ema20"] and c["ema5"] > c["ema20"]: buy += 3
        elif c["ema5"] > c["ema10"] > c["ema20"]: buy += 2
        if p["ema5"] >= p["ema20"] and c["ema5"] < c["ema20"]: sell += 3
        elif c["ema5"] < c["ema10"] < c["ema20"]: sell += 2

        buy += int(c["candle_bull"])
        sell += int(c["candle_bear"])

        return {"buy": buy, "sell": sell, "c": c, "p": p, "df": df}

    def analyze(self, df_m1, df_m5=None, df_m15=None):
        m1 = self._analyze_tf(df_m1)
        c = m1["c"]; p = m1["p"]

        trend_buy = 0; trend_sell = 0
        if df_m5 is not None and len(df_m5) >= 55:
            m5 = self._analyze_tf(df_m5)
            trend_buy += m5["buy"]; trend_sell += m5["sell"]
        if df_m15 is not None and len(df_m15) >= 55:
            m15 = self._analyze_tf(df_m15)
            trend_buy += m15["buy"]; trend_sell += m15["sell"]

        buy_score = m1["buy"] + trend_buy
        sell_score = m1["sell"] + trend_sell
        reasons_b = []; reasons_s = []

        if c["candle_names"]:
            for name in c["candle_names"]:
                if name in ("Hammer","Bullish Engulfing","Morning Star","3 White Soldiers","Tweezers Bottom"):
                    reasons_b.append(name)
                elif name in ("Shooting Star","Bearish Engulfing","Evening Star","3 Black Crows","Tweezers Top"):
                    reasons_s.append(name)

        if m1["c"]["st_dir"] == 1 and m1["p"]["st_dir"] == -1: reasons_b.append("ST Flip")
        if m1["c"]["psar_dir"] == 1 and m1["p"]["psar_dir"] == -1: reasons_b.append("PSAR Flip")
        if p["macd"] <= p["macd_signal"] and c["macd"] > c["macd_signal"]: reasons_b.append("MACD Cross")
        if p["ema5"] <= p["ema20"] and c["ema5"] > c["ema20"]: reasons_b.append("EMA 5/20 Cross")

        if m1["c"]["st_dir"] == -1 and m1["p"]["st_dir"] == 1: reasons_s.append("ST Flip")
        if m1["c"]["psar_dir"] == -1 and m1["p"]["psar_dir"] == 1: reasons_s.append("PSAR Flip")
        if p["macd"] >= p["macd_signal"] and c["macd"] < c["macd_signal"]: reasons_s.append("MACD Cross")
        if p["ema5"] >= p["ema20"] and c["ema5"] < c["ema20"]: reasons_s.append("EMA 5/20 Cross")

        price = c["close"]; rsi = c["rsi"]; atr_pips = c["atr_pips"]

        sr_levels = self._find_sr(df_m1, 60)
        if df_m5 is not None and len(df_m5) >= 20: sr_levels += self._find_sr(df_m5, 40)
        if df_m15 is not None and len(df_m15) >= 20: sr_levels += self._find_sr(df_m15, 30)

        near_sup, near_res, sup_px, res_px = self._near_sr(price, sr_levels, atr_pips)
        if near_sup: buy_score += 4; reasons_b.append(f"Support {sup_px:.2f}")
        if near_res: sell_score += 4; reasons_s.append(f"Resistance {res_px:.2f}")

        bb_upper = c["bb_upper"]; bb_lower = c["bb_lower"]
        if price <= bb_lower: buy_score += 3; reasons_b.append("BB Lower")
        elif price <= bb_lower + (bb_upper - bb_lower) * 0.15: buy_score += 2; reasons_b.append("BB Near Lower")
        if price >= bb_upper: sell_score += 3; reasons_s.append("BB Upper")
        elif price >= bb_upper - (bb_upper - bb_lower) * 0.15: sell_score += 2; reasons_s.append("BB Near Upper")

        if rsi < 30: buy_score += 2; reasons_b.append(f"RSI {rsi:.0f}")
        elif rsi < 40 and rsi > p["rsi"]: buy_score += 1
        if rsi > 70: sell_score += 2; reasons_s.append(f"RSI {rsi:.0f}")
        elif rsi > 60 and rsi < p["rsi"]: sell_score += 1

        if c["vol_ratio"] > 1.5: buy_score += 1; sell_score += 1
        elif c["vol_ratio"] > config.VOLUME_THRESHOLD: buy_score += 1; sell_score += 1

        at_peak = False
        if rsi > 75 or rsi < 25: at_peak = True
        rh = df_m1["high"].iloc[-30:].max(); rl = df_m1["low"].iloc[-30:].min()
        prange = rh - rl
        if prange > 0:
            pos_in_range = (price - rl) / prange
            if pos_in_range > 0.92 or pos_in_range < 0.08: at_peak = True

        signal = "NONE"; strength = 0; reasons = []
        if buy_score >= config.MIN_BUY_SCORE and buy_score > sell_score + 1:
            signal = "BUY"; strength = buy_score; reasons = reasons_b
        elif sell_score >= config.MIN_SELL_SCORE and sell_score > buy_score + 1:
            signal = "SELL"; strength = sell_score; reasons = reasons_s

        sl_pips = config.STOP_LOSS_PIPS
        tp_pips = config.TAKE_PROFIT_PIPS

        return {
            "signal": signal, "strength": strength, "reasons": reasons,
            "at_peak": at_peak, "rsi": round(rsi, 2), "price": round(price, 2),
            "st_dir": "UP" if c["st_dir"] == 1 else "DN",
            "psar_dir": "UP" if c["psar_dir"] == 1 else "DN",
            "macd": round(c["macd"], 4),
            "ema5": round(c["ema5"], 2), "ema10": round(c["ema10"], 2),
            "ema20": round(c["ema20"], 2),
            "bb_upper": round(bb_upper, 2), "bb_lower": round(bb_lower, 2),
            "bb_mid": round(c["bb_mid"], 2),
            "atr_pips": round(atr_pips, 2), "vol": round(c["vol_ratio"], 2),
            "sl_dist": round(sl_pips * 0.1, 4), "tp_dist": round(tp_pips * 0.1, 4),
            "sl_pips": round(sl_pips, 2), "tp_pips": round(tp_pips, 2),
            "buy_score": buy_score, "sell_score": sell_score,
        }

    def _none(self):
        return {
            "signal": "NONE", "strength": 0, "reasons": [], "at_peak": False,
            "price": 0, "rsi": 0, "macd": 0,
            "st_dir": "-", "psar_dir": "-",
            "ema5": 0, "ema10": 0, "ema20": 0,
            "bb_upper": 0, "bb_lower": 0, "bb_mid": 0,
            "atr_pips": 0, "vol": 0,
            "sl_dist": 0, "tp_dist": 0, "sl_pips": 0, "tp_pips": 0,
            "buy_score": 0, "sell_score": 0,
        }
