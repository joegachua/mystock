"""종목 검색: 티커, 영어 회사명, 일부 한글 회사명으로 티커를 찾는다."""
import yfinance as yf

# 한국 사용자가 자주 찾는 미국 주식의 한글명 매핑
_KOREAN_MAP = {
    "애플": "AAPL", "아이폰": "AAPL",
    "엔비디아": "NVDA", "엔디비아": "NVDA",
    "테슬라": "TSLA",
    "구글": "GOOGL", "알파벳": "GOOGL",
    "아마존": "AMZN",
    "마이크로소프트": "MSFT", "마소": "MSFT",
    "메타": "META", "페이스북": "META",
    "넷플릭스": "NFLX",
    "팔란티어": "PLTR",
    "아이렌": "IREN", "아이런": "IREN",
    "코닛디지털": "KRNT", "코닛": "KRNT", "코릿": "KRNT",
    "센트러스": "LEU", "센트러스에너지": "LEU",
    "에어로바이런먼트": "AVAV", "에어로바이런": "AVAV",
    "카메코": "CCJ",
    "아이온큐": "IONQ",
    "케이던스": "CDNS",
    "록히드마틴": "LMT", "록히드": "LMT", "록히드마틴코퍼레이션": "LMT",
    "몬스터베버리지": "MNST", "몬스터": "MNST",
    "노보노디스크": "NVO", "노보노디스크에이디알": "NVO",
    "알파벳a": "GOOGL", "알파벳에이": "GOOGL", "알파벳c": "GOOG", "알파벳씨": "GOOG",
    "코카콜라": "KO",
    "유나이티드헬스": "UNH", "유나이티드헬스케어": "UNH",
    "일라이릴리": "LLY", "릴리": "LLY",
    "버크셔해서웨이": "BRK-B", "버크셔": "BRK-B",
    "브로드컴": "AVGO",
    "AMD": "AMD", "에이엠디": "AMD",
    "마이크론": "MU",
    "퀄컴": "QCOM",
    "보잉": "BA",
    "디즈니": "DIS",
    "스타벅스": "SBUX",
    "맥도날드": "MCD",
    "나이키": "NKE",
    "월마트": "WMT",
    "코스트코": "COST",
    "리얼티인컴": "O",
    "엑손모빌": "XOM", "엑손": "XOM",
    "셰브론": "CVX",
    "브로드컴": "AVGO",
    "코카콜라": "KO",
    "버크셔": "BRK-B", "버크셔해서웨이": "BRK-B",
    "쿠팡": "CPNG",
    "테바": "TEVA",
    "노보노디스크": "NVO", "노보": "NVO",
    "디즈니": "DIS",
    "스타벅스": "SBUX",
    "맥도날드": "MCD",
    "나이키": "NKE",
    "비자": "V",
    "마스터카드": "MA",
    "제이피모건": "JPM", "JP모건": "JPM",
    "뱅크오브아메리카": "BAC",
    "인텔": "INTC",
    "AMD": "AMD", "에이엠디": "AMD",
    "퀄컴": "QCOM",
    "마이크론": "MU",
    "보잉": "BA",
    "에스앤피": "SPY", "S&P": "SPY", "에센피": "SPY",
    "나스닥": "QQQ", "큐큐큐": "QQQ",
}


def search_ticker(query):
    """검색어로 티커를 찾는다. 반환: (티커, 회사명) 또는 (None, None)."""
    q = query.strip()
    if not q:
        return None, None

    # 1) 한글/별칭 매핑 - 정확 매칭 (공백 제거 + 소문자)
    q_nospace = q.replace(" ", "")
    q_key = q_nospace.lower()
    for k, v in _KOREAN_MAP.items():
        if k.replace(" ", "").lower() == q_key:
            tk = v
            try:
                name = yf.Ticker(tk).info.get("shortName", tk)
            except Exception:
                name = tk
            return tk, name

    # 1-2) 한글 매핑 - 부분 매칭 (잘린 이름 대응, 예: "테바 파마슈티" -> "테바")
    #      한글이 포함된 경우에만 (영문 티커는 부분매칭하면 오매칭 위험)
    if any('\uac00' <= ch <= '\ud7a3' for ch in q):  # 한글 포함
        best = None
        for k, v in _KOREAN_MAP.items():
            kk = k.replace(" ", "").lower()
            if len(kk) < 2:
                continue
            # 입력이 키로 시작하거나, 키가 입력으로 시작 (앞부분 일치)
            if q_key.startswith(kk) or kk.startswith(q_key):
                # 더 긴(구체적인) 매칭을 우선
                if best is None or len(kk) > len(best[0]):
                    best = (kk, v)
        if best:
            tk = best[1]
            try:
                name = yf.Ticker(tk).info.get("shortName", tk)
            except Exception:
                name = tk
            return tk, name

    # 2) 입력이 티커처럼 보이면(영문/숫자 5자 이하) 바로 시도
    if len(q) <= 5 and q.replace("-", "").replace(".", "").isalnum() and q.isascii():
        tk = q.upper()
        try:
            info = yf.Ticker(tk).info
            if info.get("symbol") or info.get("shortName"):
                return tk, info.get("shortName", tk)
        except Exception:
            pass

    # 3) yfinance 검색 (영어 회사명). 미국 거래소 종목만 채택.
    def _is_us_symbol(sym):
        if not sym:
            return False
        # .TW .KS .HK 등 외국 거래소 접미사 제외 (미국은 보통 접미사 없음, BRK-B처럼 -만 허용)
        if "." in sym:
            return False
        return True
    try:
        results = yf.Search(q, max_results=8).quotes
        # 미국 보통주 우선
        for r in results:
            sym = r.get("symbol")
            if r.get("quoteType") == "EQUITY" and _is_us_symbol(sym):
                exch = (r.get("exchange") or "").upper()
                # 미국 주요 거래소만 (NMS=나스닥, NYQ=뉴욕, PCX, ASE 등). 모르면 통과시키되 접미사 없는 것만.
                return sym, r.get("shortname", sym)
        # ETF도 허용
        for r in results:
            sym = r.get("symbol")
            if r.get("quoteType") == "ETF" and _is_us_symbol(sym):
                return sym, r.get("shortname", sym)
    except Exception:
        pass

    return None, None


def get_price_history(ticker, period="20y"):
    """주가 히스토리를 반환한다. 반환: (날짜리스트, 종가리스트) 또는 ([], [])."""
    try:
        # 20년은 월별, 짧으면 더 촘촘하게
        hist = yf.Ticker(ticker).history(period=period, interval="1mo")
        if hist.empty:
            return [], []
        dates = [d.strftime("%Y-%m") for d in hist.index]
        closes = [round(float(c), 2) for c in hist["Close"]]
        return dates, closes
    except Exception:
        return [], []


# 티커 -> 대표 한글명 (역매핑). 같은 티커에 여러 별칭이 있으면 가장 대표적인 것 하나.
_TICKER_TO_KR = {}
def _build_ticker_to_kr():
    if _TICKER_TO_KR:
        return
    # 대표 한글명 우선 지정 (별칭이 여럿일 때 이걸 우선)
    preferred = {
        "AAPL": "애플", "NVDA": "엔비디아", "TSLA": "테슬라", "GOOGL": "알파벳(구글)",
        "AMZN": "아마존", "MSFT": "마이크로소프트", "META": "메타", "NFLX": "넷플릭스",
        "PLTR": "팔란티어", "AVGO": "브로드컴", "KO": "코카콜라", "BRK-B": "버크셔해서웨이",
        "CPNG": "쿠팡", "TEVA": "테바", "NVO": "노보노디스크", "DIS": "디즈니",
        "SBUX": "스타벅스", "MCD": "맥도날드", "NKE": "나이키", "V": "비자",
        "MA": "마스터카드", "JPM": "JP모건", "BAC": "뱅크오브아메리카", "INTC": "인텔",
        "AMD": "AMD", "QCOM": "퀄컴", "MU": "마이크론", "BA": "보잉",
        "SPY": "S&P500(SPY)", "QQQ": "나스닥100(QQQ)", "IREN": "아이렌",
        "KRNT": "코닛디지털", "LEU": "센트러스에너지", "AVAV": "에어로바이런먼트",
        "CCJ": "카메코", "LMT": "록히드마틴", "MNST": "몬스터베버리지",
        "UNH": "유나이티드헬스", "LLY": "일라이릴리", "IONQ": "아이온큐", "CDNS": "케이던스",
        "WMT": "월마트", "COST": "코스트코", "XOM": "엑손모빌", "CVX": "셰브론", "O": "리얼티인컴",
    }
    _TICKER_TO_KR.update(preferred)
    # 매핑에 있지만 preferred에 없는 티커는 매핑의 첫 별칭을 사용
    for kr, tk in _KOREAN_MAP.items():
        if tk not in _TICKER_TO_KR:
            _TICKER_TO_KR[tk] = kr

def korean_name(ticker):
    """티커의 한글 이름을 반환한다. 없으면 None."""
    _build_ticker_to_kr()
    return _TICKER_TO_KR.get(ticker.upper())
