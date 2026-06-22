"""SEC EDGAR에서 유명 투자자/기관의 13F 보유 종목을 가져오는 모듈."""
import urllib.request, json, re

UA = {"User-Agent": "MyStock Research contact@example.com"}

# 유명 투자자/기관 (이름: SEC CIK)
SUPER_INVESTORS = {
    "버크셔 해서웨이 (워런 버핏)": "0001067983",
    "브리지워터 (레이 달리오)": "0001350694",
    "스케일 캐피탈 (마이클 버리)": "0001649339",
    "퍼싱 스퀘어 (빌 애크먼)": "0001336528",
    "ARK 인베스트 (캐시 우드)": "0001697748",
    "듀케인 (스탠리 드러켄밀러)": "0001536411",
    "아팔루사 (데이비드 테퍼)": "0001656456",
    "빌&멜린다 게이츠 재단": "0001166559",
    "써드 포인트 (댄 러브)": "0001040273",
    "그린라이트 (데이비드 아인혼)": "0001079114",
    "코투 매니지먼트": "0001135730",
    "타이거 글로벌": "0001167483",
}

def _fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=20).read()

def _find_13f_filings(cik, n=1):
    """최근 n개의 13F-HR 보고서를 찾아 (accession_번호, 보고기준일) 리스트로 반환."""
    try:
        data = json.loads(_fetch(f"https://data.sec.gov/submissions/CIK{cik}.json"))
    except Exception:
        return []
    recent = data["filings"]["recent"]
    rds = recent.get("reportDate", [])
    out = []
    for i, form in enumerate(recent["form"]):
        if form == "13F-HR":
            acc = recent["accessionNumber"][i].replace("-", "")
            rd = rds[i] if i < len(rds) else "?"
            out.append((acc, rd))
            if len(out) >= n:
                break
    return out


def _parse_13f_holdings(cik, acc, report_date):
    """주어진 13F accession의 보유 종목을 파싱한다.
    반환: (보고기준일, [{"name","value","shares"}, ...] value 내림차순)"""
    cik_int = int(cik)
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}"
    try:
        idx = json.loads(_fetch(base + "/index.json"))
    except Exception:
        return report_date, []

    info_file = None
    # 1순위: 이름에 info/table이 들어간 xml
    for item in idx["directory"]["item"]:
        nm = item["name"].lower()
        if nm.endswith(".xml") and ("info" in nm or "table" in nm):
            info_file = item["name"]
            break
    # 2순위: primary_doc이 아닌 첫 xml
    if not info_file:
        for item in idx["directory"]["item"]:
            nm = item["name"].lower()
            if nm.endswith(".xml") and "primary_doc" not in nm:
                info_file = item["name"]
                break
    if not info_file:
        return report_date, []

    try:
        xml = _fetch(base + "/" + info_file).decode("utf-8", "ignore")
    except Exception:
        return report_date, []

    # infoTable 블록 단위로 파싱 (네임스페이스 접두사 ns1: 등도 대응)
    blocks = re.findall(r"<(?:\w+:)?infoTable>(.*?)</(?:\w+:)?infoTable>", xml, re.S)
    holdings = {}
    for b in blocks:
        nm = re.search(r"<(?:\w+:)?nameOfIssuer>(.*?)</(?:\w+:)?nameOfIssuer>", b)
        val = re.search(r"<(?:\w+:)?value>(.*?)</(?:\w+:)?value>", b)
        sh = re.search(r"<(?:\w+:)?sshPrnamt>(.*?)</(?:\w+:)?sshPrnamt>", b)
        if not nm:
            continue
        name = nm.group(1).strip()
        name = name.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        value = int(val.group(1)) if val else 0
        shares = int(sh.group(1)) if sh else 0
        if name in holdings:
            holdings[name]["value"] += value
            holdings[name]["shares"] += shares
        else:
            holdings[name] = {"name": name, "value": value, "shares": shares}

    sorted_h = sorted(holdings.values(), key=lambda x: x["value"], reverse=True)

    # 단위 자동 보정: SEC 13F는 천($1000) 단위가 표준이나 일부는 달러 단위로 보고함.
    total = sum(h["value"] for h in sorted_h)
    if total > 0 and total < 1e9:
        for h in sorted_h:
            h["value"] *= 1000
    return report_date, sorted_h


def get_13f_holdings(cik, top_n=None):
    """기관의 최신 13F 보유 종목을 반환한다. top_n=None이면 전체.
    반환: (보고기준일, [{"name","value","shares"}, ...])"""
    filings = _find_13f_filings(cik, 1)
    if not filings:
        return None, []
    acc, rd = filings[0]
    rd2, holdings = _parse_13f_holdings(cik, acc, rd)
    return rd2, (holdings if top_n is None else holdings[:top_n])


def get_13f_comparison(cik, min_change_pct=10):
    """최신 13F와 직전 분기 13F를 비교한다. 보유 '주식 수' 기준(주가 변동 영향 제거).
    반환 dict: {
      "ok": bool, "reason": (실패 시),
      "latest_date", "prev_date",
      "new":       [신규 매수 종목 ...],      # 직전엔 없고 이번에 새로 산 것
      "exited":    [전량 매도 종목 ...],      # 직전엔 있었고 이번에 사라진 것
      "increased": [비중 확대 종목 ...],      # 주식 수 +min_change_pct% 이상
      "decreased": [비중 축소 종목 ...],      # 주식 수 -min_change_pct% 이상
    }  각 항목: {"name","value","shares","prev_shares"(증감만),"change_pct"(증감만)}"""
    filings = _find_13f_filings(cik, 2)
    if len(filings) < 2:
        return {"ok": False, "reason": "비교할 직전 분기 보고서가 없어요. (보고서가 1개뿐이거나 가져오지 못했어요)"}

    (acc_new, date_new), (acc_old, date_old) = filings[0], filings[1]
    _, latest = _parse_13f_holdings(cik, acc_new, date_new)
    _, prev = _parse_13f_holdings(cik, acc_old, date_old)
    if not latest or not prev:
        return {"ok": False, "reason": "보고서 내용을 불러오지 못했어요. 잠시 후 다시 시도해주세요."}

    # 회사명이 분기마다 미세하게 다를 수 있어 정규화한 이름으로 매칭한다
    def _keyed(hlist):
        d = {}
        for h in hlist:
            k = _normalize(h["name"]) or h["name"].upper()
            if k in d:
                d[k]["value"] += h["value"]
                d[k]["shares"] += h["shares"]
            else:
                d[k] = dict(h)
        return d

    L, P = _keyed(latest), _keyed(prev)
    new, exited, increased, decreased = [], [], [], []

    for k, h in L.items():
        if k not in P:
            new.append({"name": h["name"], "value": h["value"], "shares": h["shares"]})
        else:
            ps = P[k]["shares"]
            if ps > 0:
                chg = (h["shares"] - ps) / ps * 100
                if chg >= min_change_pct:
                    increased.append({"name": h["name"], "value": h["value"],
                                      "shares": h["shares"], "prev_shares": ps,
                                      "change_pct": round(chg)})
                elif chg <= -min_change_pct:
                    decreased.append({"name": h["name"], "value": h["value"],
                                      "shares": h["shares"], "prev_shares": ps,
                                      "change_pct": round(chg)})
    for k, h in P.items():
        if k not in L:
            exited.append({"name": h["name"], "value": h["value"], "shares": h["shares"]})

    for lst in (new, exited, increased, decreased):
        lst.sort(key=lambda x: x["value"], reverse=True)

    return {"ok": True, "latest_date": date_new, "prev_date": date_old,
            "new": new, "exited": exited, "increased": increased, "decreased": decreased}


_name2ticker = {}

def _build_name_map():
    if _name2ticker:
        return
    try:
        data = json.loads(_fetch("https://www.sec.gov/files/company_tickers.json"))
        for v in data.values():
            _name2ticker[v["title"].upper()] = v["ticker"]
    except Exception:
        pass

_MANUAL_MAP = {
    "ALPHABET INC": "GOOGL", "APPLE INC": "AAPL", "AMAZON COM INC": "AMZN",
    "META PLATFORMS INC": "META", "BANK AMERICA CORP": "BAC", "BERKSHIRE HATHAWAY INC DEL": "BRK-B",
    "GREEN BRICK PARTNERS INC": "GRBK", "TESLA INC": "TSLA", "MICROSOFT CORP": "MSFT",
    "JPMORGAN CHASE & CO": "JPM", "VISA INC": "V", "MASTERCARD INC": "MA",
    "TEVA PHARMACEUTICAL INDS LTD": "TEVA", "STMICROELECTRONICS N V": "STM",
}

def _normalize(name):
    """회사명을 매칭용으로 정규화: 흔한 축약어를 풀어쓰고 접미사 제거."""
    s = name.upper()
    # 흔한 축약어 정규화
    abbrev = {
        r"\bINDS\b": "INDUSTRIES", r"\bINTL\b": "INTERNATIONAL", r"\bTECH\b": "TECHNOLOGIES",
        r"\bMFG\b": "MANUFACTURING", r"\bPHARM\b": "PHARMACEUTICAL", r"\bFINL\b": "FINANCIAL",
        r"\bSVCS\b": "SERVICES", r"\bSYS\b": "SYSTEMS", r"\bCOMMUN\b": "COMMUNICATIONS",
    }
    for a, full in abbrev.items():
        s = re.sub(a, full, s)
    suffix = r"\b(INC|CORP|CO|LTD|LLC|PLC|CL A|CL B|COM|NEW|THE|HLDGS?|HOLDINGS?|GROUP|N V|S A|DEL|TR|TRUST)\b"
    s = re.sub(suffix, "", s).strip()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def guess_ticker(company_name):
    """13F 회사명으로 티커를 추정한다. 못 찾으면 None."""
    _build_name_map()
    if not _name2ticker:
        return None
    cn = company_name.upper().strip()
    if cn in _MANUAL_MAP:
        return _MANUAL_MAP[cn]
    if cn in _name2ticker:
        return _name2ticker[cn]
    cn_norm = _normalize(company_name)
    if len(cn_norm) <= 3:
        return None
    candidates = []
    for full, tk in _name2ticker.items():
        full_norm = _normalize(full)
        if not full_norm or len(full_norm) <= 3:
            continue
        if full_norm == cn_norm or full_norm.startswith(cn_norm) or cn_norm.startswith(full_norm):
            candidates.append(tk)
    if not candidates:
        return None
    common = [t for t in candidates if "-" not in t and "." not in t and len(t) <= 5]
    chosen = common if common else candidates
    return min(chosen, key=len)


def classify_size(market_cap):
    """시가총액으로 회사 규모를 분류한다."""
    if not market_cap:
        return None, None
    if market_cap < 2e9:
        return "소형주", "#F0997B"   # 20억 달러 미만
    elif market_cap < 10e9:
        return "중형주", "#EF9F27"   # 100억 달러 미만
    else:
        return "대형주", "#8a90bf"
