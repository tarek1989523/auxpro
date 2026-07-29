import sqlite3
import logging
from typing import Optional
import config

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.db_path = config.DATABASE_PATH
        self._init()

    def _init(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    lang TEXT DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    signal TEXT NOT NULL,
                    price REAL NOT NULL,
                    sl REAL,
                    tp REAL,
                    lot REAL,
                    ticket INTEGER,
                    pnl REAL DEFAULT 0,
                    status TEXT DEFAULT 'open',
                    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_trades INTEGER DEFAULT 0,
                    total_wins INTEGER DEFAULT 0,
                    total_losses INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    daily_trades INTEGER DEFAULT 0,
                    daily_pnl REAL DEFAULT 0
                )
            """)
            conn.execute("INSERT OR IGNORE INTO stats (id) VALUES (1)")
            try:
                conn.execute("ALTER TABLE trades ADD COLUMN real_ticket INTEGER")
            except sqlite3.OperationalError:
                pass
            conn.execute("""
                CREATE TABLE IF NOT EXISTS real_accounts (
                    user_id INTEGER PRIMARY KEY,
                    login INTEGER NOT NULL,
                    password TEXT NOT NULL,
                    server TEXT NOT NULL,
                    active INTEGER DEFAULT 0,
                    platform TEXT DEFAULT 'mt5',
                    connected_at TIMESTAMP
                )
            """)
            conn.commit()

    def add_user(self, user_id: int, username: str, full_name: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                (user_id, username, full_name),
            )
            conn.commit()

    def set_lang(self, user_id: int, lang: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
            conn.commit()

    def get_lang(self, user_id: int) -> str:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return row[0] if row else "en"

    def add_trade(self, user_id: int, signal: str, price: float, sl: float,
                  tp: float, lot: float, ticket: int) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO trades (user_id, signal, price, sl, tp, lot, ticket) VALUES (?,?,?,?,?,?,?)",
                (user_id, signal, price, sl, tp, lot, ticket),
            )
            conn.execute("UPDATE stats SET total_trades = total_trades + 1, daily_trades = daily_trades + 1 WHERE id = 1")
            conn.commit()
            return cur.lastrowid

    def close_trade(self, trade_id: int, pnl: float):
        is_win = pnl > 0
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE trades SET pnl = ?, status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (pnl, trade_id),
            )
            if is_win:
                conn.execute("UPDATE stats SET total_wins = total_wins + 1, total_pnl = total_pnl + ? WHERE id = 1", (pnl,))
            else:
                conn.execute("UPDATE stats SET total_losses = total_losses + 1, total_pnl = total_pnl + ? WHERE id = 1", (pnl,))
            conn.commit()

    def set_real_ticket(self, trade_id: int, real_ticket: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE trades SET real_ticket = ? WHERE id = ?", (real_ticket, trade_id))
            conn.commit()

    def get_real_trades(self, user_id: int, limit: int = 20) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM trades WHERE user_id = ? AND real_ticket IS NOT NULL ORDER BY opened_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_open_trades(self) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM trades WHERE status = 'open'").fetchall()
            return [dict(r) for r in rows]

    def get_user_trades(self, user_id: int, limit: int = 10) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM trades WHERE user_id = ? ORDER BY opened_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM stats WHERE id = 1").fetchone()
            return dict(row) if row else {}

    def get_daily_trades(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT daily_trades FROM stats WHERE id = 1").fetchone()
            return row[0] if row else 0

    def reset_daily(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE stats SET daily_trades = 0, daily_pnl = 0 WHERE id = 1")
            conn.commit()

    def get_total_users(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def save_real_account(self, user_id: int, login: int, password: str, server: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO real_accounts (user_id, login, password, server, active, connected_at) VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)",
                (user_id, login, password, server),
            )
            conn.commit()

    def get_real_account(self, user_id: int) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM real_accounts WHERE user_id = ? AND active = 1",
                (user_id,),
            ).fetchone()
            return dict(row) if row else None

    def deactivate_real_account(self, user_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE real_accounts SET active = 0 WHERE user_id = ?", (user_id,))
            conn.commit()

    def get_all_active_real_accounts(self) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM real_accounts WHERE active = 1").fetchall()
            return [dict(r) for r in rows]
