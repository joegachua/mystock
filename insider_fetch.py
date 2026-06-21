"""SEC EDGAR에서 내부자 거래(Form 4) 상세를 가져오는 모듈."""
import urllib.request, json, re

UA = {"User-Agent": "MyStock Research contact@example.com"}
_cik_cache = {}

# 거래 코드 → 한글 의미
CODE_MAP = {
    "P": ("매수", "buy"), "S": ("매도", "sell"),
    "A": ("보상취득", "neutral"), "D": ("처분", "sell"),
    "G": ("증여", "neutral"), "M": ("옵션행사", "neutral"),
    "F": ("세금납부", "neutral"), "X": ("옵션행사", "neutral"),
    "C": ("전환", "neutral"), "J": ("기타", "neutral"),
}

def _fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=15).read()

def get_cik(ticker):
    ticker = ticker.upper()
    if not _cik_cache:
        data = json.loads(_fetch("https://www.sec.gov/files/company_tickers.json"))
        for v in data.values():
            _cik_cache[v["ticker"]] = str(v["cik_str"]).zfill(10)
    return _cik_cache.get(ticker)

def _parse_form4(xml):
    """Form 4 XML에서 핵심 정보 추출."""
    def find(tag):
        m = re.search(rf"<{tag}>(.*?)</{tag}>", xml, re.S)
        return m.group(1).strip() if m else None
    name = find("rptOwnerName") or "?"
    title = find("officerTitle")
    is_dir = find("isDirector")
    if not title:
        title = "이사" if is_dir == "1" else "내부자"
    codes = re.findall(r"<transactionCode>(.*?)</transactionCode>", xml)
    shares = re.findall(r"<transactionShares>\s*<value>(.*?)</value>", xml, re.S)
    prices = re.findall(r"<transactionPricePerShare>\s*<value>(.*?)</value>", xml, re.S)
    txns = []
    for i, code in enumerate(codes):
        kor, kind = CODE_MAP.get(code, (code, "neutral"))
        sh = shares[i] if i < len(shares) else None
        pr = prices[i] if i < len(prices) else None
        try:
            sh_num = int(float(sh)) if sh else None
        except ValueError:
            sh_num = None
        txns.append({"code": code, "label": kor, "kind": kind,
                     "shares": sh_num, "price": pr})
    return {"name": name, "title": title, "txns": txns}

def get_insider_trades(ticker, limit=8):
    """종목의 최근 내부자 거래 상세 목록을 반환한다."""
    cik = get_cik(ticker)
    if not cik:
        return []
    try:
        data = json.loads(_fetch(f"https://data.sec.gov/submissions/CIK{cik}.json"))
    except Exception:
        return []
    recent = data["filings"]["recent"]
    cik_int = int(cik)
    results = []
    for i, form in enumerate(recent["form"]):
        if form != "4":
            continue
        acc = recent["accessionNumber"][i].replace("-", "")
        date = recent["filingDate"][i]
        base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}"
        try:
            idx = json.loads(_fetch(base + "/index.json"))
            xml_file = None
            for item in idx["directory"]["item"]:
                if item["name"].endswith(".xml"):
                    xml_file = item["name"]
                    break
            if not xml_file:
                continue
            xml = _fetch(base + "/" + xml_file).decode("utf-8", "ignore")
            parsed = _parse_form4(xml)
            parsed["date"] = date
            parsed["link"] = base + "/" + xml_file
            results.append(parsed)
        except Exception:
            continue
        if len(results) >= limit:
            break
    return results
