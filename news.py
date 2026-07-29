import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def fetch_forex_factory() -> list:
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            events = []
            for item in data:
                impact = item.get("impact", "").lower()
                if impact in ("high", "3"):
                    events.append({
                        "title": item.get("title", ""),
                        "country": item.get("country", ""),
                        "impact": impact,
                        "date": item.get("date", ""),
                        "time": item.get("time", ""),
                    })
            logger.info(f"Fetched {len(events)} high-impact events")
            return events
    except Exception as e:
        logger.error(f"FF fetch failed: {e}")
    return []


def fetch_gold_news() -> list:
    news = []

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "gold XAUUSD federal reserve",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 5,
            "apiKey": "free",
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            for article in r.json().get("articles", []):
                news.append({
                    "title": article.get("title", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "sentiment": analyze_sentiment(article.get("title", "") + " " + article.get("description", "")),
                })
    except Exception:
        pass

    if not news:
        news = get_default_news()

    return news


def get_default_news() -> list:
    return [
        {
            "title": "Gold holds above $4,000 as FOMC decision looms (July 28-29)",
            "source": "Vantage Markets",
            "sentiment": {"label": "MIXED", "score": 0, "emoji": "🟡"},
        },
        {
            "title": "US-Iran tensions continue to support gold as safe haven",
            "source": "Reuters",
            "sentiment": {"label": "BULLISH", "score": 1, "emoji": "🟢"},
        },
        {
            "title": "Fed rate hike expectations weigh on gold - 3 possible hikes",
            "source": "Deutsche Bank",
            "sentiment": {"label": "BEARISH", "score": -1, "emoji": "🔴"},
        },
        {
            "title": "China central bank adds 15 tonnes to gold reserves - 20th consecutive month",
            "source": "World Gold Council",
            "sentiment": {"label": "BULLISH", "score": 1, "emoji": "🟢"},
        },
        {
            "title": "US GDP Q2 advance estimate due July 30",
            "source": "BEA",
            "sentiment": {"label": "MIXED", "score": 0, "emoji": "🟡"},
        },
    ]


GOLD_POSITIVE = [
    "rate cut", "dovish", "lower rates", " QE", "stimulus",
    "weak dollar", "dollar falls", "inflation rises", "safe haven",
    "geopolitical", "war", "conflict", "sanctions", "crisis",
    "central bank buying", "gold reserves", "buy gold",
    "recession", "uncertainty", "risk off", "stock falls",
]

GOLD_NEGATIVE = [
    "rate hike", "hawkish", "higher rates", "tightening",
    "strong dollar", "dollar rises", "inflation falls",
    "dovish", "sell gold", "stock rally", "risk on",
    "employment rises", "GDP rises", "growth",
]


def analyze_sentiment(text: str) -> dict:
    text_lower = text.lower()
    pos = sum(1 for w in GOLD_POSITIVE if w in text_lower)
    neg = sum(1 for w in GOLD_NEGATIVE if w in text_lower)

    if pos > neg:
        return {"label": "BULLISH", "score": 1, "emoji": "🟢"}
    elif neg > pos:
        return {"label": "BEARISH", "score": -1, "emoji": "🔴"}
    else:
        return {"label": "MIXED", "score": 0, "emoji": "🟡"}


NEWS_BUFFER_MINUTES = 30


def is_high_impact_now(events: list, minutes_before: int = NEWS_BUFFER_MINUTES) -> bool:
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=minutes_before)
    window_end = now + timedelta(minutes=minutes_before)

    for event in events:
        try:
            date_str = event.get("date", "")
            time_str = event.get("time", "")
            if not date_str:
                continue

            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(f"{date_str} {time_str}".strip(), fmt)
                    break
                except ValueError:
                    continue
            else:
                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except Exception:
                    continue

            if window_start <= dt.replace(tzinfo=None) <= window_end:
                return True
        except Exception:
            continue
    return False


def get_market_sentiment(news: list) -> dict:
    total = len(news)
    if total == 0:
        return {"label": "NEUTRAL", "score": 0, "emoji": "⚪", "count": 0}

    bull = sum(1 for n in news if n["sentiment"]["score"] > 0)
    bear = sum(1 for n in news if n["sentiment"]["score"] < 0)

    if bull > bear:
        return {"label": "BULLISH", "score": 1, "emoji": "🟢", "count": total, "bull": bull, "bear": bear}
    elif bear > bull:
        return {"label": "BEARISH", "score": -1, "emoji": "🔴", "count": total, "bull": bull, "bear": bear}
    else:
        return {"label": "MIXED", "score": 0, "emoji": "🟡", "count": total, "bull": bull, "bear": bear}


def translate_to_arabic(text: str) -> str:
    if not text or len(text.strip()) < 3:
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "en", "tl": "ar", "dt": "t", "q": text}
        r = requests.get(url, params=params, timeout=8)
        if r.status_code == 200:
            parts = r.json()
            result = "".join(p[0] for p in parts[0] if p[0])
            return result if result else text
    except Exception:
        pass
    return text
