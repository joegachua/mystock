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

    # 1) 한글 매핑 우선
    q_nospace = q.replace(" ", "")
    if q_nospace in _KOREAN_MAP:
        tk = _KOREAN_MAP[q_nospace]
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

    # 3) yfinance 검색 (영어 회사명)
    try:
        results = yf.Search(q, max_results=5).quotes
        # 미국 주식(보통주) 우선
        for r in results:
            if r.get("quoteType") == "EQUITY" and r.get("symbol"):
                return r["symbol"], r.get("shortname", r["symbol"])
        # 없으면 첫 결과
        if results:
            r = results[0]
            return r.get("symbol"), r.get("shortname", r.get("symbol"))
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
