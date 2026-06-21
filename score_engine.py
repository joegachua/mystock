import yfinance as yf
import numpy as np

def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))

def scale(value, low_pt, mid_pt, high_pt):
    """low_pt->0, mid_pt->50, high_pt->100 선형 환산"""
    if value is None:
        return None
    if value <= mid_pt:
        if mid_pt == low_pt:
            return 50.0
        return clamp((value - low_pt) / (mid_pt - low_pt) * 50)
    else:
        if high_pt == mid_pt:
            return 50.0
        return clamp(50 + (value - mid_pt) / (high_pt - mid_pt) * 50)

def weighted(parts):
    """parts: list of (score, weight). None인 점수는 빼고 가중치 재분배"""
    valid = [(s, w) for s, w in parts if s is not None]
    if not valid:
        return None
    total_w = sum(w for _, w in valid)
    return round(sum(s * w for s, w in valid) / total_w)

def get_volatility(ticker_obj):
    """1년 일일수익률 표준편차(연율화) -> 변동성"""
    try:
        hist = ticker_obj.history(period="1y")
        if len(hist) < 30:
            return None
        daily = hist["Close"].pct_change().dropna()
        return float(daily.std() * np.sqrt(252))  # 연율화 변동성
    except Exception:
        return None

def score_stock(ticker, user_return_pct=None):
    t = yf.Ticker(ticker)
    info = t.info
    is_etf = info.get("quoteType") == "ETF"
    name = info.get("shortName", ticker)

    result = {"ticker": ticker, "name": name, "is_etf": is_etf}

    # ===== 수익성 점수 =====
    # 1. 수익률: -50%->0, 0%->50, +100%->100
    ret_score = scale(user_return_pct, -50, 0, 100) if user_return_pct is not None else None

    # 2. 목표가 상승여력 (ETF는 없음)
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    target = info.get("targetMeanPrice")
    upside_score = None
    if price and target:
        upside = (target - price) / price * 100
        upside_score = scale(upside, -20, 0, 50)  # -20%->0, 0%->50, +50%->100
        result["upside_pct"] = round(upside, 1)

    # 애널리스트 의견 정보 (점수에는 안 쓰지만 표시/설명용)
    rec_map = {"strong_buy": "적극 매수", "buy": "매수", "hold": "중립",
               "sell": "매도", "strong_sell": "적극 매도", "underperform": "시장수익 하회",
               "outperform": "시장수익 상회"}
    rec = info.get("recommendationKey")
    if rec and rec != "none":
        result["analyst_rec"] = rec_map.get(rec, rec)
    if info.get("numberOfAnalystOpinions"):
        result["analyst_count"] = info.get("numberOfAnalystOpinions")
    if target:
        result["target_mean"] = round(target, 1)
    if info.get("targetHighPrice"):
        result["target_high"] = round(info.get("targetHighPrice"), 1)
    if info.get("targetLowPrice"):
        result["target_low"] = round(info.get("targetLowPrice"), 1)
    if price:
        result["current_price"] = round(price, 1)

    # 3. 실적 성장세 (ETF는 없음)
    growth = info.get("revenueGrowth")
    growth_score = scale(growth * 100, -10, 5, 25) if growth is not None else None

    if is_etf:
        # ETF는 수익률만으로 (목표가/성장 없음)
        result["profit_score"] = weighted([(ret_score, 1.0)])
    else:
        result["profit_score"] = weighted([
            (ret_score, 0.40),
            (upside_score, 0.35),
            (growth_score, 0.25),
        ])

    # ===== 안정성 점수 =====
    # 1. 변동성: 낮을수록 고점수 (0.2->100, 0.4->50, 0.7->0)
    vol = get_volatility(t)
    vol_score = scale(vol, 0.7, 0.4, 0.2) if vol is not None else None
    if vol is not None:
        result["volatility"] = round(vol, 2)

    # 2. 밸류에이션: PER 낮을수록 고점수 (60->0, 25->50, 10->100)
    per = info.get("trailingPE")
    per_score = scale(per, 60, 25, 10) if per is not None else None
    if per is not None:
        result["per"] = round(per, 1)

    if is_etf:
        # ETF는 변동성 + 밸류에이션만 (부채 없음, 분산효과로 가산)
        result["stability_score"] = weighted([
            (vol_score, 0.5),
            (per_score, 0.3),
            (85, 0.2),  # ETF 분산효과 보너스
        ])
    else:
        # 3. 재무 건전성: 부채비율 낮을수록 고점수 (300->0, 100->50, 0->100)
        dte = info.get("debtToEquity")
        dte_score = scale(dte, 300, 100, 0) if dte is not None else None
        if dte is not None:
            result["debt_to_equity"] = round(dte, 1)
        result["stability_score"] = weighted([
            (vol_score, 0.35),
            (per_score, 0.35),
            (dte_score, 0.30),
        ])

    return result

if __name__ == "__main__":
    tests = [("NVDA", 17.3), ("TEVA", 102.5), ("NVO", -24.5), ("SPY", 22.2)]
    for tk, ret in tests:
        r = score_stock(tk, ret)
        tag = "ETF" if r["is_etf"] else "개별주"
        print(f"\n[{r['ticker']}] {tag}")
        print(f"  수익성: {r.get('profit_score')}  안정성: {r.get('stability_score')}")
        extras = {k: v for k, v in r.items() if k in ('per','volatility','debt_to_equity','upside_pct')}
        print(f"  근거: {extras}")