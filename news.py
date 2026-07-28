import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

HIGH_IMPACT_KEYWORDS = [
    "NFP", "FOMC", "CPI", "GDP", "Interest Rate",
    "Unemployment", "Core CPI", "Retail Sales",
    "PMI", "Manufacturing", "Services",
    "Fed Chair", "Powell", "ECB", "BOE",
]

NEWS_BUFFER_MINUTES = 30


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
            logger.info(f"Fetched {len(events)} high-impact news events")
            return events
        else:
            logger.warning(f"ForexFactory API returned {r.status_code}")
            return []
    except Exception as e:
        logger.error(f"News fetch failed: {e}")
        return []


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
                logger.info(f"High impact news: {event['title']} at {dt}")
                return True

        except Exception as e:
            logger.debug(f"Parse error for event: {e}")
            continue

    return False


def get_news_summary(events: list) -> str:
    if not events:
        return "No high-impact news today"

    now = datetime.utcnow()
    upcoming = []
    for event in events:
        try:
            date_str = event.get("date", "")
            time_str = event.get("time", "")
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(f"{date_str} {time_str}".strip(), fmt)
                    break
                except ValueError:
                    continue
            else:
                continue

            if dt > now:
                diff = dt - now
                hours = int(diff.total_seconds() // 3600)
                mins = int((diff.total_seconds() % 3600) // 60)
                upcoming.append({
                    "title": event["title"],
                    "time": f"{hours}h {mins}m",
                    "country": event.get("country", "?"),
                })
        except Exception:
            continue

    if not upcoming:
        return "No upcoming high-impact news"

    lines = []
    for u in upcoming[:5]:
        lines.append(f"  {u['country']} | {u['title']} | in {u['time']}")

    return "\n".join(lines)
