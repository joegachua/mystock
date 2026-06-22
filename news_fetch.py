"""yfinance로 종목 관련 최신 뉴스를 가져오는 모듈."""
import yfinance as yf
import time

def get_news(ticker, limit=4):
    """종목 티커의 최신 뉴스 목록을 반환한다. [{title, publisher, link, time}, ...]"""
    items = []
    for attempt in range(3):
        try:
            items = yf.Ticker(ticker).news or []
            if items:
                break
        except Exception:
            items = []
        if attempt < 2:
            time.sleep(0.7 * (attempt + 1))  # 0.7, 1.4초

    out = []
    for it in items[:limit]:
        c = it.get("content", it)
        title = c.get("title")
        if not title:
            continue
        publisher = ""
        prov = c.get("provider")
        if isinstance(prov, dict):
            publisher = prov.get("displayName", "")
        link = ""
        curl = c.get("canonicalUrl") or c.get("clickThroughUrl")
        if isinstance(curl, dict):
            link = curl.get("url", "")
        elif isinstance(c.get("link"), str):
            link = c["link"]
        when = ""
        pub = c.get("pubDate") or c.get("displayTime")
        if pub:
            when = str(pub)[:10]
        # 본문 요약(있으면) — AI가 '무슨 일이 왜 일어났는지'를 파악하는 데 쓴다
        summary = c.get("summary") or c.get("description") or ""
        if isinstance(summary, str):
            summary = summary.strip()
            if len(summary) > 600:        # 너무 길면 잘라 토큰 절약
                summary = summary[:600] + "…"
        else:
            summary = ""
        out.append({"title": title, "publisher": publisher, "link": link,
                    "time": when, "summary": summary})
    return out
