"""
Gold Trading Bot - Telegram + MT5
Features: Auto trading, real account copy trading, multi-timeframe strategy
"""
import asyncio
import logging
import datetime
import re
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

import config
from database import Database
import mt5_manager as mt5
from strategy import Strategy
from news import fetch_forex_factory, is_high_impact_now, fetch_gold_news, get_market_sentiment, translate_to_arabic

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot_log.txt"), logging.StreamHandler()],
)
logger = logging.getLogger("GoldBot")

db = Database()
strategy = Strategy()
trading_active = {}
bot_app = None
_cache = {"df": None, "df5": None, "df15": None, "time": 0}

LANG = {
    "ar": {
        "restart": "⭐ ابدأ من جديد",
        "start": "── ═══════════════ ──\n      نظام التداول الذهبية\n── ═══════════════ ──\n\nاختر من القائمة:",
        "account": "الحساب التجريبي",
        "real_account": "الحساب الحقيقي",
        "trade": "ابدأ التداول",
        "stop": "أوقف التداول",
        "positions": "الصفقات المفتوحة",
        "analyze": "تحليل السوق",
        "results": "النتائج",
        "settings": "الإعدادات",
        "help": "المساعدة",
        "back": "العودة",
        "admin": "لوحة التحكم",
        "news": "الأخبار",
        "lang_btn": "English",
        "trading_on": "التداول يعمل الآن",
        "trading_off": "تم إيقاف التداول",
        "no_pos": "لا توجد صفقات مفتوحة",
        "connecting": "جاري الاتصال بالـ MT5...",
        "connected": "تم الاتصال بالحساب التجريبي",
        "failed": "فشل الاتصال بالـ MT5",
        "report": "التقرير اليومي",
        "login": "رقم الحساب",
        "server": "السيرفر",
        "balance": "الرصيد",
        "equity": "الحقوق",
        "profit": "الربح",
        "status": "الحالة",
        "active": "نشط",
        "inactive": "غير نشط",
        "no_data": "لا توجد بيانات",
        "signal": "الإشارة",
        "score": "النتيجة",
        "at_peak": "قمة/قاع",
        "price": "السعر",
        "timeframes": "الإطارات الزمنية",
        "total_trades": "إجمالي الصفقات",
        "wins": "الأرباح",
        "losses": "الخسائر",
        "win_rate": "نسبة النجاح",
        "denied": "ممنوع",
        "users": "المستخدمين",
        "news_title": "أخبار الذهب والتحليل",
        "safe_to_trade": "آمن للتداول",
        "stop_trading": "أوقف التداول",
        "market": "السوق",
        "bullish": "صاعد",
        "bearish": "هابط",
        "economic_calendar": "التقويم الاقتصادي",
        "copied_to_real": "✅ تم النسخ للحساب الحقيقي",
        "real_connected": "موصل ✅",
        "real_copying": "يتم نسخ الصفقات تلقائياً",
        "real_no_account": "ليس لديك حساب متصل.",
        "real_send_format": "أرسل بيانات حسابك بهذا التنسيق:",
        "real_format": "الرقم|كلمة السر|اسم السيرفر",
        "real_example": "مثال:",
        "real_disconnected": "تم فصل الحساب الحقيقي ✅",
        "real_disconnect_btn": "فصل الحساب",
        "real_error_digits": "❌ خطأ: رقم الحساب يجب أن يكون أرقام فقط",
        "real_saved": "✅ تم حفظ بيانات الحساب الحقيقي",
        "real_will_copy": "سيتم نسخ الصفقات تلقائياً عند فتحها.",
        "real_wrong_format": "❌ تنسيق غير صحيح",
        "account_info": "معلومات الحساب",
        "analysis": "التحليل الفني",
        "peak_yes": "نعم - تجنب",
        "peak_no": "لا",
        "symbol": "الرمز",
        "lot": "العقد",
        "max_positions": "الحد الأقصى للصفقات",
        "scan_interval": "وقت المسح",
        "indicators": "المؤشرات",
        "trailing_stop": "وقف متحرك",
        "min_score": "الحد الأدنى للنتيجة",
        "help_trade": "1. اختر \"ابدأ التداول\"",
        "help_scan": "2. البوت يمسح السوق كل",
        "help_auto": "3. يفتح صفقات XAUUSD تلقائياً",
        "help_sltp": "4. الوقف/الهدف يغلق الصفقات تلقائياً",
        "help_check": "5. تحقق من النتائج لمعرفة الأداء",
        "seconds": "ثانية",
        "trades": "صفقات",
    },
    "en": {
        "restart": "⭐ Restart",
        "start": "── ═══════════════ ──\n    Gold Trading System\n── ═══════════════ ──\n\nChoose from menu:",
        "account": "Demo Account",
        "real_account": "Real Account",
        "trade": "Start Trading",
        "stop": "Stop Trading",
        "positions": "Open Positions",
        "analyze": "Market Analysis",
        "results": "Results",
        "settings": "Settings",
        "help": "Help",
        "back": "Back",
        "admin": "Admin Panel",
        "news": "News",
        "lang_btn": "عربي",
        "trading_on": "Trading active",
        "trading_off": "Trading stopped",
        "no_pos": "No open positions",
        "connecting": "Connecting to MT5...",
        "connected": "Connected to demo account",
        "failed": "MT5 connection failed",
        "report": "Daily Report",
        "login": "Login",
        "server": "Server",
        "balance": "Balance",
        "equity": "Equity",
        "profit": "Profit",
        "status": "Status",
        "active": "Active",
        "inactive": "Inactive",
        "no_data": "No data",
        "signal": "Signal",
        "score": "Score",
        "at_peak": "At Peak",
        "price": "Price",
        "timeframes": "Timeframes",
        "total_trades": "Total Trades",
        "wins": "Wins",
        "losses": "Losses",
        "win_rate": "Win Rate",
        "denied": "Denied",
        "users": "Users",
        "news_title": "Gold News & Analysis",
        "safe_to_trade": "Safe to trade",
        "stop_trading": "STOP TRADING",
        "market": "Market",
        "bullish": "Bullish",
        "bearish": "Bearish",
        "economic_calendar": "Economic Calendar",
        "copied_to_real": "✅ Copied to Real Account",
        "real_connected": "Connected ✅",
        "real_copying": "Trades are copied automatically",
        "real_no_account": "You don't have a connected account.",
        "real_send_format": "Send your account details in this format:",
        "real_format": "login|password|server",
        "real_example": "Example:",
        "real_disconnected": "Real account disconnected ✅",
        "real_disconnect_btn": "Disconnect",
        "real_error_digits": "❌ Error: Login must contain only numbers",
        "real_saved": "✅ Real account saved",
        "real_will_copy": "Trades will be copied automatically when opened.",
        "real_wrong_format": "❌ Invalid format",
        "account_info": "Account Info",
        "analysis": "Technical Analysis",
        "peak_yes": "YES - Avoid",
        "peak_no": "NO",
        "symbol": "Symbol",
        "lot": "Lot",
        "max_positions": "Max Positions",
        "scan_interval": "Scan Interval",
        "indicators": "Indicators",
        "trailing_stop": "Trailing Stop",
        "min_score": "Min Score",
        "help_trade": "1. Choose \"Start Trading\"",
        "help_scan": "2. Bot scans market every",
        "help_auto": "3. Opens XAUUSD trades automatically",
        "help_sltp": "4. SL/TP close trades automatically",
        "help_check": "5. Check Results for performance",
        "seconds": "sec",
        "trades": "Trades",
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
    btns = [
        [InlineKeyboardButton(L(uid, "restart"), callback_data="restart")],
        [InlineKeyboardButton(L(uid, "account"), callback_data="acct"),
         InlineKeyboardButton(L(uid, "real_account"), callback_data="real_acct")],
        [InlineKeyboardButton(L(uid, "trade"), callback_data="start_trade"),
         InlineKeyboardButton(L(uid, "stop"), callback_data="stop_trade")],
        [InlineKeyboardButton(L(uid, "positions"), callback_data="positions"),
         InlineKeyboardButton(L(uid, "analyze"), callback_data="analyze")],
        [InlineKeyboardButton(L(uid, "news"), callback_data="news"),
         InlineKeyboardButton(L(uid, "results"), callback_data="results")],
        [InlineKeyboardButton(L(uid, "settings"), callback_data="settings"),
         InlineKeyboardButton(L(uid, "help"), callback_data="help")],
        [InlineKeyboardButton(L(uid, "lang_btn"), callback_data="lang_toggle")],
    ]
    if is_admin(uid):
        btns.insert(3, [InlineKeyboardButton(L(uid, "admin"), callback_data="admin")])
    return kb(uid, btns)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    uid = u.id
    db.add_user(uid, u.username or "", u.full_name or "")
    lang = db.get_lang(uid)
    if lang:
        await update.message.reply_text(L(uid, "start"), reply_markup=main_menu(uid))
    else:
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
    await q.answer()

    if d == "lang_ar":
        db.set_lang(uid, "ar")
        await q.edit_message_text(L(uid, "start"), reply_markup=main_menu(uid))
        return

    if d == "lang_en":
        db.set_lang(uid, "en")
        await q.edit_message_text(L(uid, "start"), reply_markup=main_menu(uid))
        return

    if d == "lang_toggle":
        lang = db.get_lang(uid)
        db.set_lang(uid, "en" if lang == "ar" else "ar")
        await q.edit_message_text(L(uid, "start"), reply_markup=main_menu(uid))
        return

    if d == "back" or d == "restart":
        await q.edit_message_text(L(uid, "start"), reply_markup=main_menu(uid))
        return

    if d == "acct":
        info = await asyncio.to_thread(mt5.account_info)
        if info:
            txt = (
                f"{'─'*30}\n"
                f"  {L(uid, 'account')}\n"
                f"{'─'*30}\n\n"
                f"{L(uid, 'login')}: {info['login']}\n"
                f"{L(uid, 'server')}: {info['server']}\n"
                f"{L(uid, 'balance')}: {info['balance']:.2f}$\n"
                f"{L(uid, 'equity')}: {info['equity']:.2f}$\n"
                f"{L(uid, 'profit')}: {info['profit']:.2f}$\n\n"
                f"{L(uid, 'status')}: {L(uid, 'active') if trading_active.get(uid) else L(uid, 'inactive')}"
            )
        else:
            txt = L(uid, "failed")
        await q.answer()
        await q.edit_message_text(txt, reply_markup=kb(uid, [[InlineKeyboardButton(L(uid, "back"), callback_data="back")]]))
        return

    if d == "real_acct":
        ra = await asyncio.to_thread(db.get_real_account, uid)
        if ra:
            txt = (
                f"{'─'*30}\n"
                f"  {L(uid, 'real_account')}\n"
                f"{'─'*30}\n\n"
                f"{L(uid, 'login')}: {ra['login']}\n"
                f"{L(uid, 'server')}: {ra['server']}\n"
                f"{L(uid, 'real_connected')}\n\n"
                f"{L(uid, 'real_copying')}"
            )
            btns = [[InlineKeyboardButton(L(uid, "real_disconnect_btn"), callback_data="real_disconnect"),
                     InlineKeyboardButton(L(uid, "back"), callback_data="back")]]
        else:
            txt = (
                f"{'─'*30}\n"
                f"  {L(uid, 'real_account')}\n"
                f"{'─'*30}\n\n"
                f"{L(uid, 'real_no_account')}\n\n"
                f"{L(uid, 'real_send_format')}\n"
                f"`{L(uid, 'real_format')}`\n\n"
                f"{L(uid, 'real_example')}:\n"
                f"`12345678|MyPassword|MetaQuotes-Demo`"
            )
            btns = [[InlineKeyboardButton(L(uid, "back"), callback_data="back")]]
        await q.answer()
        await q.edit_message_text(txt, reply_markup=kb(uid, btns))
        return

    if d == "real_disconnect":
        await asyncio.to_thread(db.deactivate_real_account, uid)
        await q.answer(L(uid, "real_disconnected"), show_alert=True)
        await q.edit_message_text(L(uid, "start"), reply_markup=main_menu(uid))
        return

    if d == "start_trade":
        await q.answer()
        await q.edit_message_text(L(uid, "connecting"))

        connected = await asyncio.to_thread(mt5.connect, config.DEMO_LOGIN, config.DEMO_PASSWORD, config.DEMO_SERVER)
        if connected:
            info = await asyncio.to_thread(mt5.account_info)
            trading_active[uid] = True
            bal = f"{info['balance']:.2f}$" if info else "?"

            df = _cache.get("df")
            df5 = _cache.get("df5")
            df15 = _cache.get("df15")
            cached_age = datetime.datetime.now().timestamp() - _cache.get("time", 0) if _cache.get("time") else 999
            if df is None or cached_age > 15:
                df = await asyncio.to_thread(mt5.get_ohlcv, config.TIMEFRAME, 250)
                df5 = await asyncio.to_thread(mt5.get_ohlcv, "M5", 250)
                df15 = await asyncio.to_thread(mt5.get_ohlcv, "M15", 250)
                if df is not None:
                    _cache.update(df=df, df5=df5, df15=df15, time=datetime.datetime.now().timestamp())
            analysis = strategy.analyze(df, df5, df15) if df is not None else {"signal": "NONE"}

            txt = (
                f"{'─'*30}\n"
                f"  {L(uid, 'connected')}\n"
                f"{'─'*30}\n\n"
                f"{L(uid, 'login')}: {info['login']}\n"
                f"{L(uid, 'balance')}: {bal}\n"
                f"{L(uid, 'scan_interval')}: {config.SCAN_INTERVAL_SECONDS}s\n\n"
                f"{L(uid, 'signal')}: {analysis['signal']}\n"
                f"{L(uid, 'wins')}: {analysis.get('buy_score', 0)} | {L(uid, 'losses')}: {analysis.get('sell_score', 0)}\n"
                f"{L(uid, 'status')}: {L(uid, 'trading_on')}"
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
        df = _cache.get("df")
        df5 = _cache.get("df5")
        df15 = _cache.get("df15")
        cached_age = datetime.datetime.now().timestamp() - _cache.get("time", 0) if _cache.get("time") else 999
        if df is None or cached_age > 15:
            connected = await asyncio.to_thread(mt5.connect, config.DEMO_LOGIN, config.DEMO_PASSWORD, config.DEMO_SERVER)
            if connected:
                df = await asyncio.to_thread(mt5.get_ohlcv, config.TIMEFRAME, 250)
                df5 = await asyncio.to_thread(mt5.get_ohlcv, "M5", 250)
                df15 = await asyncio.to_thread(mt5.get_ohlcv, "M15", 250)
                if df is not None:
                    _cache.update(df=df, df5=df5, df15=df15, time=datetime.datetime.now().timestamp())
        if df is not None:
            a = strategy.analyze(df, df5, df15)
            peak = L(uid, "peak_yes") if a.get("at_peak") else L(uid, "peak_no")
            txt = (
                f"{'─'*30}\n  {L(uid, 'analysis')}\n{'─'*30}\n\n"
                f"{L(uid, 'signal')}: {a['signal']}\n"
                f"{L(uid, 'score')}: {a['strength']}\n"
                f"{L(uid, 'wins')}: {a['buy_score']} | {L(uid, 'losses')}: {a['sell_score']}\n"
                f"{L(uid, 'at_peak')}: {peak}\n"
                f"{'─'*30}\n"
                f"{L(uid, 'price')}: {a['price']}\n"
                f"SuperTrend: {a['st_dir']}\n"
                f"PSAR: {a['psar_dir']}\n"
                f"MACD: {a['macd']}\n"
                f"RSI: {a['rsi']}\n"
                f"EMA 5/10/20: {a['ema5']}/{a['ema10']}/{a['ema20']}\n"
                f"ATR: {a['atr_pips']:.1f} pips\n"
                f"Volume: {a['vol']}x\n\n"
                f"SL: {a['sl_pips']:.1f} pips\n"
                f"TP: {a['tp_pips']:.1f} pips\n"
                f"{L(uid, 'timeframes')}: M1+M5+M15"
            )
            if a["reasons"]:
                txt += f"\n\n{', '.join(a['reasons'])}"
        else:
            txt = L(uid, "no_data")
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
            f"{L(uid, 'total_trades')}: {trades}\n"
            f"{L(uid, 'wins')}: {wins} | {L(uid, 'losses')}: {losses}\n"
            f"{L(uid, 'win_rate')}: {wr:.1f}%\n\n"
            f"P/L: {pnl:+.2f}$"
        )
        await q.answer()
        await q.edit_message_text(txt, reply_markup=kb(uid, [[InlineKeyboardButton(L(uid, "back"), callback_data="back")]]))
        return

    if d == "settings":
        txt = (
            f"{'─'*30}\n  {L(uid, 'settings')}\n{'─'*30}\n\n"
            f"{L(uid, 'symbol')}: {config.SYMBOL}\n"
            f"{L(uid, 'timeframes')}: {config.TIMEFRAME}\n"
            f"{L(uid, 'lot')}: {config.LOT_SIZE}\n"
            f"{L(uid, 'max_positions')}: {config.MAX_POSITIONS}\n"
            f"{L(uid, 'scan_interval')}: {config.SCAN_INTERVAL_SECONDS}s\n\n"
            f"{L(uid, 'indicators')}:\n"
            f"  SuperTrend (10, 3.0)\n"
            f"  Parabolic SAR\n"
            f"  MACD\n"
            f"  EMA 5/10/20\n"
            f"  RSI 14\n"
            f"  Volume\n"
            f"  ATR (dynamic)\n\n"
            f"{L(uid, 'timeframes')}: M1 + M5 + M15\n"
            f"{L(uid, 'trailing_stop')}: ON\n"
            f"{L(uid, 'min_score')}: {config.MIN_BUY_SCORE}"
        )
        await q.answer()
        await q.edit_message_text(txt, reply_markup=kb(uid, [[InlineKeyboardButton(L(uid, "back"), callback_data="back")]]))
        return

    if d == "help":
        txt = (
            f"{'─'*30}\n  {L(uid, 'help')}\n{'─'*30}\n\n"
            f"{L(uid, 'help_trade')}\n"
            f"{L(uid, 'help_scan')} {config.SCAN_INTERVAL_SECONDS} {L(uid, 'seconds')}\n"
            f"{L(uid, 'help_auto')}\n"
            f"{L(uid, 'help_sltp')}\n"
            f"{L(uid, 'help_check')}"
        )
        await q.answer()
        await q.edit_message_text(txt, reply_markup=kb(uid, [[InlineKeyboardButton(L(uid, "back"), callback_data="back")]]))
        return

    if d == "admin":
        if not is_admin(uid):
            await q.answer(L(uid, "denied"), show_alert=True)
            return
        total = db.get_total_users()
        s = db.get_stats()
        txt = (
            f"{'─'*30}\n  {L(uid, 'admin')}\n{'─'*30}\n\n"
            f"{L(uid, 'users')}: {total}\n"
            f"{L(uid, 'trades')}: {s.get('total_trades', 0)}\n"
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
        status = L(uid, "stop_trading") if now_trading else L(uid, "safe_to_trade")

        lang = db.get_lang(uid)
        if lang == "ar" and sentiment.get("label"):
            sentiment["label"] = await asyncio.to_thread(translate_to_arabic, sentiment["label"])

        txt = (
            f"{'─'*30}\n  {L(uid, 'news_title')}\n{'─'*30}\n\n"
            f"{L(uid, 'status')}: {status}\n"
            f"{L(uid, 'market')}: {sentiment['emoji']} {sentiment['label']}\n"
            f"{L(uid, 'bullish')}: {sentiment.get('bull', 0)} | {L(uid, 'bearish')}: {sentiment.get('bear', 0)}\n\n"
        )

        for i, n in enumerate(news[:5], 1):
            s = n["sentiment"]
            title = n["title"][:60]
            if lang == "ar":
                title = await asyncio.to_thread(translate_to_arabic, title)
            txt += f"{s['emoji']} {title}\n   {n['source']}\n\n"

        if events:
            txt += f"{'─'*30}\n  {L(uid, 'economic_calendar')}\n{'─'*30}\n\n"
            for e in events[:3]:
                title = e['title']
                if lang == "ar":
                    title = await asyncio.to_thread(translate_to_arabic, title)
                txt += f"  {e['country']} | {title}\n"

        await q.edit_message_text(txt, reply_markup=main_menu(uid))
        return

    await q.answer()


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    parts = text.split("|")
    if len(parts) == 3:
        login_str, password, server = parts
        login_str = login_str.strip()
        if not login_str.isdigit():
            await update.message.reply_text(
                f"{L(uid, 'real_error_digits')}\n\n"
                f"{L(uid, 'real_send_format')}:\n"
                f"`{L(uid, 'real_format')}`"
            )
            return
        login = int(login_str)
        await asyncio.to_thread(db.save_real_account, uid, login, password, server)
        await update.message.reply_text(
            f"{L(uid, 'real_saved')}\n\n"
            f"{L(uid, 'login')}: {login}\n"
            f"{L(uid, 'server')}: {server}\n\n"
            f"{L(uid, 'real_will_copy')}"
        )
    else:
        await update.message.reply_text(
            f"{L(uid, 'real_wrong_format')}\n\n"
            f"{L(uid, 'real_send_format')}:\n"
            f"`{L(uid, 'real_format')}`\n\n"
            f"{L(uid, 'real_example')}:\n"
            "`12345678|MyPassword|MetaQuotes-Demo`"
        )


async def copy_to_real(order_type: str, lot: float, sl: float, tp: float, price: float) -> bool:
    accounts = await asyncio.to_thread(db.get_all_active_real_accounts)
    if not accounts:
        return False
    copied = 0
    for acc in accounts:
        try:
            ok = await asyncio.to_thread(mt5.connect, acc["login"], acc["password"], acc["server"])
            if ok:
                res = await asyncio.to_thread(mt5.open_order, order_type, lot, sl, tp)
                if res:
                    copied += 1
                    logger.info(f"Copied to real {acc['login']}: {order_type} #{res['ticket']}")
        except Exception as e:
            logger.error(f"Copy failed to {acc['login']}: {e}")
    await asyncio.to_thread(mt5.connect, config.DEMO_LOGIN, config.DEMO_PASSWORD, config.DEMO_SERVER)
    return copied > 0


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
        connected = await asyncio.to_thread(mt5.connect, config.DEMO_LOGIN, config.DEMO_PASSWORD, config.DEMO_SERVER)
        if not connected:
            logger.error("MT5 connect failed")
            return

        events = await asyncio.to_thread(fetch_forex_factory)
        if is_high_impact_now(events):
            return

        df = await asyncio.to_thread(mt5.get_ohlcv, config.TIMEFRAME, 250)
        if df is None:
            return

        df5 = await asyncio.to_thread(mt5.get_ohlcv, "M5", 250)
        df15 = await asyncio.to_thread(mt5.get_ohlcv, "M15", 250)

        global _cache
        _cache["df"] = df
        _cache["df5"] = df5
        _cache["df15"] = df15
        _cache["time"] = datetime.datetime.now().timestamp()

        analysis = strategy.analyze(df, df5, df15)
        sig = analysis["signal"]
        logger.info(f"Scan: {sig} buy={analysis['buy_score']} sell={analysis['sell_score']} trend={analysis.get('trend','?')}")

        if sig not in ("BUY", "SELL"):
            return

        signal = sig

        pos = await asyncio.to_thread(mt5.get_positions)

        for p in pos:
            if p["profit"] >= config.PROFIT_CLOSE_AMOUNT:
                await asyncio.to_thread(mt5.close_position, p["ticket"])

        remaining = config.MAX_POSITIONS - len(pos)
        if remaining <= 0:
            return

        price = analysis["price"]
        sl = price - analysis["sl_dist"] if signal == "BUY" else price + analysis["sl_dist"]
        tp = price + analysis["tp_dist"] if signal == "BUY" else price - analysis["tp_dist"]

        same_dir = [p for p in pos if p["type"] == signal]
        same_count = len(same_dir)
        open_count = min(config.TRADES_PER_SIGNAL - same_count, remaining)
        if same_count >= config.TRADES_PER_SIGNAL:
            open_count = 0

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
            copied = await copy_to_real(signal, config.LOT_SIZE, sl, tp, price)
            emoji = "🟢" if signal == "BUY" else "🔴"
            reasons_str = ", ".join(analysis["reasons"]) if analysis["reasons"] else "-"
            txt = (
                f"{emoji} {len(opened)}x {signal}\n"
                f"{'─'*30}\n\n"
                f"{L(0, 'price')}: {price}\n"
                f"{L(0, 'lot')}: {config.LOT_SIZE}\n"
                f"SL: {sl:.2f} ({analysis['sl_pips']:.1f} pips)\n"
                f"TP: {tp:.2f} ({analysis['tp_pips']:.1f} pips)\n\n"
                f"{L(0, 'score')}: {analysis['strength']}/12\n"
                f"SuperTrend: {analysis['st_dir']}\n"
                f"RSI: {analysis['rsi']}\n"
                f"Volume: {analysis['vol']}x\n\n"
                f"Reasons: {reasons_str}\n"
                f"{L(uid, 'wins')}: {len(opened)} | {L(uid, 'losses')}: {failed}"
            )
            if copied:
                txt += f"\n\n{L(uid, 'copied_to_real')}"
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handler))
    app.job_queue.run_repeating(trading_loop, interval=config.SCAN_INTERVAL_SECONDS, first=10)
    app.job_queue.run_daily(daily_reset, time=datetime.time(hour=0, minute=0))
    logger.info("Bot running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
