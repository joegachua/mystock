import yfinance as yf

def get_news(ticker, limit=4):
    try:
        items = yf.Ticker(ticker).news or []
    except Exception:
        return []
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
        out.append({"title": title, "publisher": publisher, "link": link, "time": when})
    return out
