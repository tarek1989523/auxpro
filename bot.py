import asyncio
import logging
import datetime
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import config
from database import Database
import mt5_manager as mt5
from strategy import Strategy
from news import fetch_forex_factory, is_high_impact_now, fetch_gold_news, get_market_sentiment

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger("GoldBot")

db = Database()
strategy = Strategy()
trading_active = {}
bot_app = None

LANG = {
    "ar": {
        "start": "── ═══════════════ ──\n      نظام التداول الذهبية\n── ═══════════════ ──\n\nاختر من القائمة:",
        "account": "الحساب التجريبي",
        "trade": "ابدأ التداول",
        "stop": "أوقف التداول",
        "positions": "الصفقات المفتوحة",
        "analyze": "تحليل السوق",
        "results": "النتائج",
        "settings": "الإعدادات",
        "help": "المساعدة",
        "back": "العودة",
        "admin": "لوحة التحكم",
        "lang_btn": "English",
        "trading_on": "التداول يعمل الآن",
        "trading_off": "تم إيقاف التداول",
        "no_pos": "لا توجد صفقات مفتوحة",
        "connecting": "جاري الاتصال بالـ MT5...",
        "connected": "تم الاتصال بالحساب التجريبي",
        "failed": "فشل الاتصال بالـ MT5",
        "report": "التقرير اليومي",
    },
    "en": {
        "start": "── ═══════════════ ──\n    Gold Trading System\n── ═══════════════ ──\n\nChoose from menu:",
        "account": "Demo Account",
        "trade": "Start Trading",
        "stop": "Stop Trading",
        "positions": "Open Positions",
        "analyze": "Market Analysis",
        "results": "Results",
        "settings": "Settings",
        "help": "Help",
        "back": "Back",
        "admin": "Admin Panel",
        "lang_btn": "عربي",
        "trading_on": "Trading active",
        "trading_off": "Trading stopped",
        "no_pos": "No open positions",
        "connecting": "Connecting to MT5...",
        "connected": "Connected to demo account",
        "failed": "MT5 connection failed",
        "report": "Daily Report",
    },
}


def L(user_id: int, key: str) -> str:
    lang = db.get_lang(user_id)
    return LANG.get(lang, LANG["en"]).get(key, key)


def is_admin(uid: int) -> bool:
    return uid in config.ADMIN_USERS


def kb(uid: int, rows: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(rows)


def main_menu(uid: int) -> InlineKeyboardMarkup:
    lang = db.get_lang(uid)
    btns = [
        [InlineKeyboardButton(L(uid, "account"), callback_data="acct")],
        [InlineKeyboardButton(L(uid, "trade"), callback_data="start_trade"),
         InlineKeyboardButton(L(uid, "stop"), callback_data="stop_trade")],
        [InlineKeyboardButton(L(uid, "positions"), callback_data="positions"),
         InlineKeyboardButton(L(uid, "analyze"), callback_data="analyze")],
        [InlineKeyboardButton("News", callback_data="news"),
         InlineKeyboardButton(L(uid, "results"), callback_data="results")],
        [InlineKeyboardButton(L(uid, "settings"), callback_data="settings"),
         InlineKeyboardButton(L(uid, "help"), callback_data="help")],
        [InlineKeyboardButton(L(uid, "lang_btn"), callback_data="lang_toggle")],
    ]
    if is_admin(uid):
        btns.insert(2, [InlineKeyboardButton(L(uid, "admin"), callback_data="admin")])
    return kb(uid, btns)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.add_user(u.id, u.username or "", u.full_name or "")
    await update.message.reply_text(
        L(u.id, "start"),
        reply_markup=kb(uid=u.id, rows=[
            [InlineKeyboardButton("English", callback_data="lang_en"),
             InlineKeyboardButton("عربي", callback_data="lang_ar")],
        ]),
    )


async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data
    uid = q.from_user.id

    if d == "lang_ar":
        db.set_lang(uid, "ar")
        await q.answer()
        await q.edit_message_text(L(uid, "start"), reply_markup=main_menu(uid))
        return

    if d == "lang_en":
        db.set_lang(uid, "en")
        await q.answer()
        await q.edit_message_text(L(uid, "start"), reply_markup=main_menu(uid))
        return

    if d == "lang_toggle":
        lang = db.get_lang(uid)
        db.set_lang(uid, "en" if lang == "ar" else "ar")
        await q.answer()
        await q.edit_message_text(L(uid, "start"), reply_markup=main_menu(uid))
        return

    if d == "back":
        await q.answer()
        await q.edit_message_text(L(uid, "start"), reply_markup=main_menu(uid))
        return

    if d == "acct":
        info = await asyncio.to_thread(mt5.account_info)
        if info:
            txt = (
                f"{'─'*30}\n"
                f"  {L(uid, 'account')}\n"
                f"{'─'*30}\n\n"
                f"Login: {info['login']}\n"
                f"Server: {info['server']}\n"
                f"Balance: {info['balance']:.2f}$\n"
                f"Equity: {info['equity']:.2f}$\n"
                f"Profit: {info['profit']:.2f}$\n\n"
                f"Status: {'Active' if trading_active.get(uid) else 'Inactive'}"
            )
        else:
            txt = L(uid, "failed")
        await q.answer()
        await q.edit_message_text(txt, reply_markup=kb(uid, [[InlineKeyboardButton(L(uid, "back"), callback_data="back")]]))
        return

    if d == "start_trade":
        await q.answer()
        await q.edit_message_text(L(uid, "connecting"))

        connected = await asyncio.to_thread(mt5.connect, config.DEMO_LOGIN, config.DEMO_PASSWORD, config.DEMO_SERVER)
        if connected:
            info = await asyncio.to_thread(mt5.account_info)
            trading_active[uid] = True
            bal = f"{info['balance']:.2f}$" if info else "?"

            df = await asyncio.to_thread(mt5.get_ohlcv, config.TIMEFRAME, 250)
            df5 = await asyncio.to_thread(mt5.get_ohlcv, "M5", 250)
            df15 = await asyncio.to_thread(mt5.get_ohlcv, "M15", 250)
            analysis = strategy.analyze(df, df5, df15) if df is not None else {"signal": "NONE"}

            txt = (
                f"{'─'*30}\n"
                f"  {L(uid, 'connected')}\n"
                f"{'─'*30}\n\n"
                f"Account: {info['login']}\n"
                f"Balance: {bal}\n"
                f"Scan: {config.SCAN_INTERVAL_SECONDS}s\n\n"
                f"Market: {analysis['signal']}\n"
                f"Buy: {analysis.get('buy_score', 0)} | Sell: {analysis.get('sell_score', 0)}\n"
                f"Status: Trading ACTIVE"
            )
        else:
            txt = L(uid, "failed")
        await q.edit_message_text(txt, reply_markup=main_menu(uid))
        return

    if d == "stop_trade":
        trading_active[uid] = False
        await q.answer(L(uid, "trading_off"), show_alert=True)
        await q.edit_message_text(L(uid, "trading_off"), reply_markup=main_menu(uid))
        return

    if d == "positions":
        connected = await asyncio.to_thread(mt5.connect, config.DEMO_LOGIN, config.DEMO_PASSWORD, config.DEMO_SERVER)
        if connected:
            pos = await asyncio.to_thread(mt5.get_positions)
            if pos:
                txt = f"{'─'*30}\n  {L(uid, 'positions')}\n{'─'*30}\n\n"
                for p in pos:
                    s = "+" if p["profit"] >= 0 else ""
                    txt += f"{p['type']} | {p['volume']} lot | {s}{p['profit']:.2f}$\n"
            else:
                txt = L(uid, "no_pos")
        else:
            txt = L(uid, "failed")
        await q.answer()
        await q.edit_message_text(txt, reply_markup=main_menu(uid))
        return

    if d == "analyze":
        await q.answer()
        connected = await asyncio.to_thread(mt5.connect, config.DEMO_LOGIN, config.DEMO_PASSWORD, config.DEMO_SERVER)
        if connected:
            df = await asyncio.to_thread(mt5.get_ohlcv, config.TIMEFRAME, 250)
            df5 = await asyncio.to_thread(mt5.get_ohlcv, "M5", 250)
            df15 = await asyncio.to_thread(mt5.get_ohlcv, "M15", 250)
            if df is not None:
                a = strategy.analyze(df, df5, df15)
                peak = "YES - SKIP" if a.get("at_peak") else "NO"
                txt = (
                    f"{'─'*30}\n  {L(uid, 'analyze')}\n{'─'*30}\n\n"
                    f"Signal: {a['signal']}\n"
                    f"Score: {a['strength']}\n"
                    f"Buy: {a['buy_score']} | Sell: {a['sell_score']}\n"
                    f"At Peak: {peak}\n"
                    f"{'─'*30}\n"
                    f"Price: {a['price']}\n"
                    f"SuperTrend: {a['st_dir']}\n"
                    f"PSAR: {a['psar_dir']}\n"
                    f"MACD: {a['macd']}\n"
                    f"RSI: {a['rsi']}\n"
                    f"EMA: {a['ema5']}/{a['ema10']}/{a['ema20']}\n"
                    f"ATR: {a['atr_pips']:.1f} pips\n"
                    f"Volume: {a['vol']}x\n\n"
                    f"SL: {a['sl_pips']:.1f} pips\n"
                    f"TP: {a['tp_pips']:.1f} pips\n"
                    f"Timeframes: M1+M5+M15"
                )
                if a["reasons"]:
                    txt += f"\n\n{', '.join(a['reasons'])}"
            else:
                txt = "No data"
        else:
            txt = L(uid, "failed")
        await q.edit_message_text(txt, reply_markup=main_menu(uid))
        return

    if d == "results":
        s = db.get_stats()
        trades = s.get("total_trades", 0)
        wins = s.get("total_wins", 0)
        losses = s.get("total_losses", 0)
        pnl = s.get("total_pnl", 0)
        wr = (wins / trades * 100) if trades > 0 else 0
        txt = (
            f"{'─'*30}\n  {L(uid, 'results')}\n{'─'*30}\n\n"
            f"Total Trades: {trades}\n"
            f"Wins: {wins} | Losses: {losses}\n"
            f"Win Rate: {wr:.1f}%\n\n"
            f"P/L: {pnl:+.2f}$"
        )
        await q.answer()
        await q.edit_message_text(txt, reply_markup=kb(uid, [[InlineKeyboardButton(L(uid, "back"), callback_data="back")]]))
        return

    if d == "settings":
        txt = (
            f"{'─'*30}\n  {L(uid, 'settings')}\n{'─'*30}\n\n"
            f"Symbol: {config.SYMBOL}\n"
            f"Timeframe: {config.TIMEFRAME}\n"
            f"Lot: {config.LOT_SIZE}\n"
            f"Max Positions: {config.MAX_POSITIONS}\n"
            f"Scan: {config.SCAN_INTERVAL_SECONDS}s\n\n"
            f"Indicators:\n"
            f"  SuperTrend (10, 3.0)\n"
            f"  Parabolic SAR\n"
            f"  MACD\n"
            f"  EMA 5/10/20\n"
            f"  RSI 14\n"
            f"  Volume\n"
            f"  ATR (dynamic SL/TP)\n\n"
            f"Timeframes: M1 + M5 + M15\n"
            f"Peak Detection: ON\n"
            f"Trailing Stop: ON\n"
            f"Min Score: {config.MIN_BUY_SCORE}"
        )
        await q.answer()
        await q.edit_message_text(txt, reply_markup=kb(uid, [[InlineKeyboardButton(L(uid, "back"), callback_data="back")]]))
        return

    if d == "help":
        txt = (
            f"{'─'*30}\n  {L(uid, 'help')}\n{'─'*30}\n\n"
            f"1. {L(uid, 'trade')}\n"
            f"2. Bot scans market every {config.SCAN_INTERVAL_SECONDS}s\n"
            f"3. Opens XAUUSD trades automatically\n"
            f"4. SL/TP close trades automatically\n"
            f"5. Check {L(uid, 'results')} for performance"
        )
        await q.answer()
        await q.edit_message_text(txt, reply_markup=kb(uid, [[InlineKeyboardButton(L(uid, "back"), callback_data="back")]]))
        return

    if d == "admin":
        if not is_admin(uid):
            await q.answer("Denied", show_alert=True)
            return
        total = db.get_total_users()
        s = db.get_stats()
        txt = (
            f"{'─'*30}\n  {L(uid, 'admin')}\n{'─'*30}\n\n"
            f"Users: {total}\n"
            f"Trades: {s.get('total_trades', 0)}\n"
            f"P/L: {s.get('total_pnl', 0):+.2f}$"
        )
        await q.answer()
        await q.edit_message_text(txt, reply_markup=kb(uid, [[InlineKeyboardButton(L(uid, "back"), callback_data="back")]]))
        return

    if d == "news":
        await q.answer()
        events = await asyncio.to_thread(fetch_forex_factory)
        now_trading = is_high_impact_now(events)
        news = await asyncio.to_thread(fetch_gold_news)
        sentiment = get_market_sentiment(news)
        status = "STOP TRADING" if now_trading else "Safe to trade"

        txt = (
            f"{'─'*30}\n  Gold News & Analysis\n{'─'*30}\n\n"
            f"Status: {status}\n"
            f"Market: {sentiment['emoji']} {sentiment['label']}\n"
            f"Bullish: {sentiment.get('bull', 0)} | Bearish: {sentiment.get('bear', 0)}\n\n"
        )

        for i, n in enumerate(news[:5], 1):
            s = n["sentiment"]
            txt += f"{s['emoji']} {n['title'][:60]}\n   Source: {n['source']}\n\n"

        if events:
            txt += f"{'─'*30}\n  Economic Calendar\n{'─'*30}\n\n"
            for e in events[:3]:
                txt += f"  {e['country']} | {e['title']}\n"

        await q.edit_message_text(txt, reply_markup=main_menu(uid))
        return

    await q.answer()


async def notify_admin(text: str):
    global bot_app
    if not bot_app:
        return
    for uid in config.ADMIN_USERS:
        try:
            await bot_app.bot.send_message(chat_id=uid, text=text)
        except Exception as e:
            logger.error(f"Notify failed to {uid}: {e}")


async def trading_loop(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        await asyncio.to_thread(mt5.trailing_stop)

        daily = db.get_daily_trades()
        if daily >= config.MAX_DAILY_TRADES:
            logger.info(f"Daily limit reached: {daily}/{config.MAX_DAILY_TRADES}")
            return

        events = await asyncio.to_thread(fetch_forex_factory)
        if is_high_impact_now(events):
            logger.info("Skipping - high impact news")
            return

        connected = await asyncio.to_thread(mt5.connect, config.DEMO_LOGIN, config.DEMO_PASSWORD, config.DEMO_SERVER)
        if not connected:
            logger.info("MT5 not connected")
            return

        df = await asyncio.to_thread(mt5.get_ohlcv, config.TIMEFRAME, 250)
        df5 = await asyncio.to_thread(mt5.get_ohlcv, "M5", 250)
        df15 = await asyncio.to_thread(mt5.get_ohlcv, "M15", 250)
        if df is None:
            logger.info("No OHLCV data")
            return

        analysis = strategy.analyze(df, df5, df15)
        sig = analysis["signal"]
        logger.info(f"Scan: signal={sig} buy={analysis['buy_score']} sell={analysis['sell_score']} daily={daily}/{config.MAX_DAILY_TRADES}")

        if sig not in ("BUY", "SELL"):
            return

        pos = await asyncio.to_thread(mt5.get_positions)
        remaining = config.MAX_POSITIONS - len(pos)
        if remaining <= 0:
            return

        signal = analysis["signal"]
        price = analysis["price"]
        sl = price - analysis["sl_dist"] if signal == "BUY" else price + analysis["sl_dist"]
        tp = price + analysis["tp_dist"] if signal == "BUY" else price - analysis["tp_dist"]

        same_dir = [p for p in pos if p["type"] == signal]
        same_count = len(same_dir)

        if same_count == 0:
            open_count = min(5, remaining)
        elif same_count < 10:
            open_count = min(3, remaining)
        elif same_count < 20:
            open_count = min(2, remaining)
        else:
            open_count = min(1, remaining)

        if open_count <= 0:
            return

        opened = []
        failed = 0

        for i in range(open_count):
            result = await asyncio.to_thread(mt5.open_order, signal, config.LOT_SIZE, sl, tp)
            if result:
                db.add_trade(0, signal, result["price"], sl, tp, config.LOT_SIZE, result["ticket"])
                opened.append(result["ticket"])
            else:
                failed += 1

        if opened:
            emoji = "🟢" if signal == "BUY" else "🔴"
            reasons_str = ", ".join(analysis["reasons"]) if analysis["reasons"] else "-"
            txt = (
                f"{emoji} {len(opened)}x {signal} Trades Opened\n"
                f"{'─'*30}\n\n"
                f"Price: {price}\n"
                f"Lot each: {config.LOT_SIZE}\n"
                f"Total lot: {config.LOT_SIZE * len(opened)}\n"
                f"SL: {sl:.2f} ({analysis['sl_pips']:.1f} pips)\n"
                f"TP: {tp:.2f} ({analysis['tp_pips']:.1f} pips)\n\n"
                f"Score: {analysis['strength']}/12\n"
                f"SuperTrend: {analysis['st_dir']}\n"
                f"PSAR: {analysis['psar_dir']}\n"
                f"MACD: {analysis['macd']}\n"
                f"RSI: {analysis['rsi']}\n"
                f"Volume: {analysis['vol']}x\n\n"
                f"Reasons: {reasons_str}\n"
                f"Opened: {len(opened)} | Failed: {failed}"
            )
            await notify_admin(txt)
            logger.info(f"Opened {len(opened)}x {signal} trades")

    except Exception as e:
        logger.error(f"Loop error: {e}")


async def daily_reset(ctx: ContextTypes.DEFAULT_TYPE):
    db.reset_daily()
    logger.info("Daily stats reset")


async def post_init(app: Application):
    await app.bot.set_my_commands([BotCommand("start", "Start")])


def main():
    global bot_app
    logger.info("Starting Gold Trading Bot...")
    app = Application.builder().token(config.TELEGRAM_TOKEN).post_init(post_init).build()
    bot_app = app
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(handler))
    app.job_queue.run_repeating(trading_loop, interval=config.SCAN_INTERVAL_SECONDS, first=10)
    app.job_queue.run_daily(daily_reset, time=datetime.time(hour=0, minute=0))
    logger.info("Bot running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
