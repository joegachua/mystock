import streamlit as st
from score_engine import score_stock as _score_stock
from ai_explain import init_client, explain_stock, summarize_news, extract_holdings_from_images, summarize_insider, analyze_government_policy, analyze_sector_policy_timeline, diagnose_portfolio, analyze_remarks_overview, analyze_remarks_sector, analyze_trending_sectors, analyze_sector_focus, analyze_holding_thesis
from news_fetch import get_news as _get_news
from insider_fetch import get_insider_trades as _get_insider_trades
from superinvestor_fetch import get_13f_holdings as _get_13f_holdings, SUPER_INVESTORS, guess_ticker as _guess_ticker, get_13f_comparison as _get_13f_comparison
from stock_search import search_ticker as _search_ticker, get_price_history as _get_price_history

# ── 캐싱 래퍼 ──────────────────────────────────────────────
# 같은 종목/데이터를 반복 조회할 때 메모리에 잠시 저장해 속도·서버 부담을 줄인다.
@st.cache_data(ttl=600, show_spinner=False)   # 점수: 10분
def score_stock(ticker, user_return_pct=None):
    return _score_stock(ticker, user_return_pct)

@st.cache_data(ttl=600, show_spinner=False)   # 뉴스: 10분 (결과 있을 때만 캐시)
def _get_news_cached(ticker, limit=4):
    result = _get_news(ticker, limit)
    return result

def get_news(ticker, limit=4):
    # 빈 결과가 캐시에 박히면 10분간 빈 뉴스가 나오므로, 빈 결과는 캐시를 비우고 재시도 여지를 남긴다
    result = _get_news_cached(ticker, limit)
    if not result:
        _get_news_cached.clear()
    return result

@st.cache_data(ttl=1800, show_spinner=False)  # 내부자 거래: 30분
def get_insider_trades(ticker, limit=8):
    return _get_insider_trades(ticker, limit)

@st.cache_data(ttl=3600, show_spinner=False)  # 13F: 1시간 (분기마다 바뀌므로 길게)
def get_13f_holdings(cik, top_n=None):
    return _get_13f_holdings(cik, top_n)

@st.cache_data(ttl=3600, show_spinner=False)  # 13F 분기 비교: 1시간
def get_13f_comparison(cik):
    return _get_13f_comparison(cik)

@st.cache_data(ttl=3600, show_spinner=False)  # 스마트머니 랭킹: 1시간
def compute_smart_money_ranking(top_each=20):
    """등록된 모든 슈퍼투자자의 최신 13F 상위 종목을 모아, 같은 종목을 몇 명이
    공통으로 보유했는지 집계한다. 반환: [{ticker, name, holders[], count, total_value}, ...]
    (보유한 투자자 수 → 총 보유금액 순 내림차순)"""
    agg = {}  # 티커(없으면 정규화 이름) -> 집계
    for inv, cik in SUPER_INVESTORS.items():
        _rd, holdings = get_13f_holdings(cik, top_each)   # 캐싱됨
        if not holdings:
            continue
        for h in holdings:
            tk = guess_ticker(h["name"])                  # 캐싱됨
            key = tk or h["name"].upper()
            if key not in agg:
                agg[key] = {"ticker": tk or "", "name": h["name"],
                            "holders": set(), "value": 0}
            agg[key]["holders"].add(inv)
            agg[key]["value"] += h.get("value", 0)
    out = []
    for v in agg.values():
        out.append({"ticker": v["ticker"], "name": v["name"],
                    "holders": sorted(v["holders"]),
                    "count": len(v["holders"]), "total_value": v["value"]})
    out.sort(key=lambda x: (x["count"], x["total_value"]), reverse=True)
    return out

@st.cache_data(ttl=86400, show_spinner=False) # 회사명→티커 매칭: 하루
def guess_ticker(company_name):
    return _guess_ticker(company_name)

@st.cache_data(ttl=3600, show_spinner=False)  # 검색: 1시간
def search_ticker(query):
    return _search_ticker(query)

@st.cache_data(ttl=3600, show_spinner=False)  # 주가 차트: 1시간
@st.cache_data(ttl=3600, show_spinner=False)
def get_price_history(ticker, period="20y", interval="1mo"):
    return _get_price_history(ticker, period, interval)
# ───────────────────────────────────────────────────────────

st.set_page_config(page_title="포트폴리오 점수 분석", page_icon="🚀", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Gowun+Dodum&family=Noto+Sans+KR:wght@400;500;700&display=swap');
.stApp {
    background:
      radial-gradient(2px 2px at 20% 30%, #ffffff 50%, transparent 50%),
      radial-gradient(2px 2px at 60% 70%, #ffffff 50%, transparent 50%),
      radial-gradient(1.5px 1.5px at 50% 50%, #cfd4ff 50%, transparent 50%),
      radial-gradient(1.5px 1.5px at 80% 20%, #ffffff 50%, transparent 50%),
      radial-gradient(2px 2px at 90% 60%, #ffffff 50%, transparent 50%),
      radial-gradient(1.5px 1.5px at 33% 85%, #cfd4ff 50%, transparent 50%),
      radial-gradient(2px 2px at 15% 65%, #ffffff 50%, transparent 50%),
      radial-gradient(1.5px 1.5px at 70% 40%, #ffffff 50%, transparent 50%),
      radial-gradient(ellipse at top, #131a3a 0%, #0a0e1f 55%, #05070f 100%);
    background-size: 400px 400px, 350px 350px, 300px 300px, 450px 450px, 380px 380px, 420px 420px, 360px 360px, 320px 320px, 100% 100%;
    animation: starscroll 120s linear infinite;
}
@keyframes starscroll {
    from { background-position: 0 0,0 0,0 0,0 0,0 0,0 0,0 0,0 0,0 0; }
    to   { background-position: 400px 400px,-350px 350px,300px -300px,-450px 200px,380px -380px,200px 420px,-360px 360px,320px -320px,0 0; }
}
.block-container { position: relative; z-index: 1; }
html, body, [class*="css"], .stMarkdown, p, label, textarea, input {
    font-family: 'Noto Sans KR','Gowun Dodum',sans-serif !important;
}
h1 { font-family: 'Orbitron','Noto Sans KR',sans-serif !important; color: #F4F5FF !important; letter-spacing: 1px; text-shadow: 0 0 18px rgba(127,119,221,0.6); }
h2, h3, h4 { font-family: 'Orbitron','Noto Sans KR',sans-serif !important; color: #E5E2FF !important; letter-spacing: 0.5px; }
p, label, .stCaption, span { color: #C5C9E8 !important; }
.stTextArea textarea, .stTextInput input {
    background: rgba(20,26,58,0.85) !important; color: #FFFFFF !important;
    border: 1px solid rgba(175,169,236,0.4) !important; font-size: 15px !important;
}
[data-testid="stMetric"] { background: rgba(127,119,221,0.12); border: 0.5px solid rgba(175,169,236,0.3); border-radius: 12px; padding: 14px 16px; }
[data-testid="stMetricValue"] { color: #FFFFFF !important; font-family: 'Orbitron',sans-serif !important; }
[data-testid="stMetricLabel"] p { color: #AFA9EC !important; }
[data-testid="stExpander"] { background: rgba(28,34,72,0.75) !important; border: 0.5px solid rgba(175,169,236,0.25) !important; border-radius: 12px !important; margin-bottom: 8px; }
[data-testid="stExpander"] summary p { color: #F4F5FF !important; font-weight: 500 !important; font-family: 'Noto Sans KR',sans-serif !important; }
[data-testid="stExpander"] summary {
    background: transparent !important;
}
[data-testid="stExpander"] summary:hover {
    background: rgba(127,119,221,0.15) !important;
}
[data-testid="stExpander"] details[open] summary {
    background: transparent !important;
}
[data-testid="stExpander"] details[open] {
    background: rgba(28,34,72,0.75) !important;
}
[data-testid="stExpander"] summary svg { fill: #AFA9EC !important; }
[data-testid="stExpander"] span[data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded','Material Icons' !important; color: #AFA9EC !important; }
.stButton button {
    background: rgba(127,119,221,0.06) !important; color: #D5D8F0 !important;
    border: 1px solid rgba(175,169,236,0.35) !important;
    border-radius: 10px !important; font-weight: 500 !important;
    font-family: 'Noto Sans KR',sans-serif !important; letter-spacing: 0;
    padding: 11px 18px !important; box-shadow: none !important; transition: all 0.18s ease;
    text-align: left !important; justify-content: flex-start !important; display: flex !important;
}
.stButton button:hover {
    background: rgba(127,119,221,0.16) !important;
    border-color: rgba(175,169,236,0.65) !important;
    color: #F4F5FF !important;
}
.stButton button > div, .stButton button p, .stButton button > div > p {
    text-align: left !important; width: 100% !important; justify-content: flex-start !important;
    display: block !important;
}
/* primary 버튼(전체 분석, 보유 종목 보기 등)은 채운 보라색 + 가운데 */
.stButton button[kind="primary"] {
    background: #7F77DD !important; color: #ffffff !important; border: none !important;
    font-weight: 700 !important; font-family: 'Orbitron','Noto Sans KR',sans-serif !important;
    letter-spacing: 0.5px; box-shadow: 0 0 16px rgba(127,119,221,0.5) !important;
    text-align: center !important; justify-content: center !important;
}
.stButton button[kind="primary"]:hover { background: rgba(127,119,221,0.7) !important; box-shadow: 0 0 10px rgba(127,119,221,0.3) !important; }
.stButton button[kind="primary"] > div, .stButton button[kind="primary"] p { text-align: center !important; }
hr { border-color: rgba(175,169,236,0.2) !important; }
/* 입력 표(data_editor) - 테두리/둥근모서리 (색은 config.toml 다크테마가 처리) */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    border: 1px solid rgba(175,169,236,0.35) !important;
    border-radius: 12px !important; overflow: hidden !important;
}
[data-testid="stSidebar"] { background: rgba(10,14,31,0.95) !important; }
header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { background: transparent !important; }
[data-testid="stExpander"] details > div,
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    background: transparent !important;
}
[data-testid="stExpander"] > details,
[data-testid="stExpander"] > details > summary,
[data-testid="stExpander"] [class*="st-emotion"] {
    background-color: transparent !important;
}
[data-testid="stExpander"] [data-testid="stVerticalBlock"],
[data-testid="stExpander"] [data-testid="stHorizontalBlock"] {
    background: transparent !important;
}
[data-testid="stAlert"] {
    background: rgba(127,119,221,0.12) !important;
    border: 0.5px solid rgba(175,169,236,0.3) !important;
}
[data-testid="stAlert"] p { color: #E5E2FF !important; }

</style>
""", unsafe_allow_html=True)

def clean_name(name):
    return name.replace("*", "").strip() if name else name

def ai_text_box(text, tone="purple"):
    """AI 생성 텍스트를 통일된 스타일의 박스로 표시한다. tone: purple(기본)/green/orange"""
    if not text:
        return
    safe = text.replace("#", "").replace("**", "").replace("\n", "<br>")
    tones = {
        "purple": ("rgba(127,119,221,0.12)", "rgba(175,169,236,0.3)"),
        "green":  ("rgba(93,202,165,0.10)",  "rgba(93,202,165,0.3)"),
        "orange": ("rgba(240,153,123,0.10)", "rgba(240,153,123,0.3)"),
    }
    bg, border = tones.get(tone, tones["purple"])
    st.markdown(
        f"<div style='background:{bg};border:0.5px solid {border};border-radius:10px;"
        f"padding:14px 16px;margin:8px 0;color:#E5E2FF;font-size:14px;line-height:1.85'>{safe}</div>",
        unsafe_allow_html=True)


def policy_ticker_section(tickers, key_prefix, names=None):
    """정책 분석에서 나온 관련 종목 후보를 버튼으로 보여주고, 누르면 점수 카드를 표시한다.
    검색 결과와 분야 타임라인이 공통으로 사용한다. key_prefix로 위젯/세션 키를 분리한다.
    names: {티커: 영어 회사명} (있으면 버튼에 함께 표시)."""
    names = names or {}
    if not tickers:
        st.caption("이번 분석에서는 직접 관련된 개별 종목이 특정되지 않았어요.")
        return
    st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)
    st.subheader("정책과 관련해 언급된 종목")
    st.caption("AI가 위 분석에서 언급한 종목이에요. 눌러보면 이 앱의 점수·지표로 살펴볼 수 있어요. (추천이 아닙니다)")
    cols = st.columns(2)
    for i, tk in enumerate(tickers):
        eng = names.get(tk, "")
        label = f"{tk} · {eng}" if eng else tk
        if cols[i % 2].button(label, key=f"{key_prefix}_btn_{tk}", use_container_width=True):
            st.session_state[f"{key_prefix}_pick"] = tk
            st.session_state.pop(f"{key_prefix}_pick_ai", None)

    pick = st.session_state.get(f"{key_prefix}_pick")
    if not pick:
        return
    st.divider()
    r = None
    try:
        with st.spinner(f"{pick} 분석 중…"):
            r = score_stock(pick, None)
    except Exception:
        r = None
    if not r:
        st.warning(f"{pick} 데이터를 가져오지 못했어요. 잠시 후 다시 시도하거나 '종목 검색' 탭에서 찾아보세요.")
        return
    nm = clean_name(r.get("name", pick))
    tag = "ETF" if r.get("is_etf") else "개별주"
    st.markdown(f"#### {pick} · {nm} ({tag})")
    m1, m2, m3 = st.columns(3)
    m1.metric("수익성 점수", f"{r.get('profit_score','-')}/100")
    m2.metric("안정성 점수", f"{r.get('stability_score','-')}/100")
    if r.get("current_price") is not None:
        m3.metric("현재가", f"${r.get('current_price')}")
    bits = []
    if r.get("per") is not None: bits.append(f"PER {r['per']}")
    if r.get("analyst_rec"): bits.append(f"애널리스트 의견: {r['analyst_rec']}")
    if r.get("upside_pct") is not None: bits.append(f"목표가 상승여력 {r['upside_pct']}%")
    if bits:
        st.caption(" · ".join(str(b) for b in bits))
    if f"{key_prefix}_pick_ai" not in st.session_state:
        with st.spinner("AI가 이 종목을 설명하는 중…"):
            st.session_state[f"{key_prefix}_pick_ai"] = explain_stock(r)
    ai_text_box(st.session_state.get(f"{key_prefix}_pick_ai", ""), tone="green")
    st.caption("더 자세히 보려면 '종목 검색' 탭에서 같은 티커를 검색해보세요.")


def policy_sources_expander(data):
    """정책/발언 분석 결과의 출처·검색어를 접이식으로 보여준다.
    data dict는 _grounded_generate 형식({sources, queries, ...})을 따른다."""
    sources = data.get("sources") or []
    queries = data.get("queries") or []
    if not (sources or queries):
        st.caption("이번 분석에서는 표시할 출처를 가져오지 못했어요. (검색이 일어나지 않았을 수 있어요)")
        return
    with st.expander(f"🔎 AI가 참고한 출처 {len(sources)}개 보기"):
        if queries:
            st.markdown(
                "<div style='color:#9BA0C4;font-size:12px;margin-bottom:6px'>AI 검색어: "
                + ", ".join(f"<span style='color:#AFA9EC'>{q}</span>" for q in queries)
                + "</div>", unsafe_allow_html=True)
        for s in sources:
            title = s.get("title") or s.get("uri")
            uri = s.get("uri")
            st.markdown(
                f"<div style='font-size:13px;margin:3px 0'>• "
                f"<a href='{uri}' target='_blank' style='color:#9BC4FF;text-decoration:none'>{title}</a></div>",
                unsafe_allow_html=True)


@st.cache_data(ttl=1800, show_spinner=False)
def get_usdkrw():
    """현재 원/달러 환율을 가져온다(30분 캐시). 실패하면 None."""
    import yfinance as yf
    for sym in ("KRW=X", "USDKRW=X"):
        try:
            h = yf.Ticker(sym).history(period="5d")
            if not h.empty:
                v = float(h["Close"].dropna().iloc[-1])
                if v > 100:           # 정상 환율 범위 방어
                    return round(v, 1)
        except Exception:
            pass
    return None


# ===== 사이드바: 메뉴 + Gemini API 키 =====
with st.sidebar:
    st.markdown("### 메뉴")
    page = st.radio("페이지 선택", ["내 포트폴리오 분석", "부자들은 요즘 뭘 샀나", "종목 검색", "미국 정부·정책 분석", "관심 많은 분야"],
                    label_visibility="collapsed")
    st.divider()
    st.markdown("### 설정")
    api_key = st.text_input("Gemini API 키", type="password",
                            help="aistudio.google.com/apikey 에서 무료 발급")
    if api_key:
        init_client(api_key)
        st.success("AI 설명 사용 가능")
    else:
        st.caption("키를 넣으면 AI 설명이 켜져요.")

if page == "내 포트폴리오 분석":
    st.markdown(
        "<div style='border-bottom:1px solid rgba(175,169,236,0.2);padding-bottom:14px;margin-bottom:18px'>"
        "<div style='font-size:28px;font-weight:700;font-family:Orbitron,sans-serif;color:#F4F5FF;letter-spacing:0.5px;text-shadow:0 0 18px rgba(127,119,221,0.5)'>PORTFOLIO INTELLIGENCE</div>"
        "<div style='color:#9BA0C4;font-size:14px;margin-top:4px'>내 포트폴리오를 수익성·안정성 두 축으로 평가하고, AI가 해석해드립니다.</div>"
        "</div>",
        unsafe_allow_html=True)
    st.markdown("<div style='color:#9BA0C4;font-size:13px;margin-bottom:6px'>아래 표에 종목 티커와 수익률을 입력하세요. 행은 자유롭게 추가·삭제할 수 있습니다.</div>", unsafe_allow_html=True)

    _fx = get_usdkrw()
    if _fx:
        st.markdown(
            f"<div style='background:rgba(127,119,221,0.08);border:0.5px solid rgba(175,169,236,0.25);"
            f"border-radius:8px;padding:8px 12px;margin-bottom:12px;font-size:13px;color:#C5C9E8'>"
            f"💱 현재 환율 <b style='color:#AFA9EC'>1달러 ≈ {_fx:,.1f}원</b> "
            f"<span style='color:#6E7396'>· 미국 주식은 달러로 사고팔아요. 환율이 오르면(원화 약세) 주가가 그대로여도 원화 평가액은 커지고, "
            f"내리면 반대예요. 즉 <b>실제 수익엔 '주가 + 환율'이 같이 작용</b>해요.</span></div>",
            unsafe_allow_html=True)

    with st.expander("포트폴리오 캡처로 자동 입력 (토스 등)"):
        st.caption("캡처에 종목명과 수익률이 보이게 찍어주세요. 여러 장도 가능합니다.")
        st.caption("💡 팁: 영어 티커(AAPL, NVDA)가 보이게 캡처하면 인식이 더 정확해요. "
                   "토스에서 종목을 누르면 상세 화면에 티커가 나옵니다.")
        uploaded = st.file_uploader("캡처 이미지", type=["png", "jpg", "jpeg"],
                                    accept_multiple_files=True, label_visibility="collapsed")
        if st.button("이미지에서 종목 인식"):
            if not api_key:
                st.warning("왼쪽 사이드바에 Gemini API 키를 먼저 넣어주세요.")
            elif not uploaded:
                st.warning("캡처 이미지를 먼저 올려주세요.")
            else:
                with st.spinner("AI가 캡처에서 종목을 읽는 중..."):
                    imgs = [f.read() for f in uploaded]
                    result, err = extract_holdings_from_images(imgs)
                if err:
                    st.error(err)
                elif result:
                    import yfinance as yf
                    from stock_search import korean_name
                    holdings = result.get("holdings", [])
                    unresolved = result.get("unresolved", [])
                    rows = []
                    with st.spinner("인식한 종목을 확인하는 중..."):
                        for d in holdings:
                            tk = d.get("ticker", "")
                            # 한글명 우선, 없으면 정식 영문명
                            kr = korean_name(tk)
                            nm = d.get("name", "")
                            try:
                                info = yf.Ticker(tk).info
                                if info.get("shortName"):
                                    nm = info.get("shortName")
                            except Exception:
                                pass
                            rows.append({"티커": tk, "한글명": kr or "", "종목명": nm, "수익률(%)": d.get("return_pct")})
                    st.session_state["holdings_df"] = rows
                    msg = f"{len(rows)}개 종목을 인식했어요. 아래 표에서 확인하고 수정하세요."
                    if unresolved:
                        msg += f"\n\n⚠️ 티커를 못 찾은 종목: {', '.join(unresolved)}. 표에 직접 추가해주세요."
                    st.success(msg)
                    st.rerun()

    import pandas as pd
    default_rows = st.session_state.get("holdings_df", [
        {"티커": "NVDA", "한글명": "엔비디아", "종목명": "NVIDIA", "수익률(%)": 17.3},
        {"티커": "TEVA", "한글명": "테바", "종목명": "Teva", "수익률(%)": 102.5},
        {"티커": "NVO", "한글명": "노보노디스크", "종목명": "Novo Nordisk", "수익률(%)": -24.5},
        {"티커": "GOOGL", "한글명": "알파벳(구글)", "종목명": "Alphabet", "수익률(%)": 30.9},
        {"티커": "SPY", "한글명": "S&P500(SPY)", "종목명": "SPDR S&P 500", "수익률(%)": 22.2},
        {"티커": "CPNG", "한글명": "쿠팡", "종목명": "Coupang", "수익률(%)": -6.1},
    ])
    df_init = pd.DataFrame(default_rows)
    df_init.index = range(1, len(df_init) + 1)
    df_init.index.name = "No."
    editor_ver = st.session_state.get("editor_ver", 0)
    edited = st.data_editor(
        df_init,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=False,
        column_order=["티커", "한글명", "종목명", "수익률(%)"],
        column_config={
            "티커": st.column_config.TextColumn("티커", help="예: NVDA", width="small", pinned=True),
            "한글명": st.column_config.TextColumn("한글명", help="한국어 종목 이름", width="medium"),
            "종목명": st.column_config.TextColumn("종목명(영문)", help="정식 회사 이름", width="medium"),
            "수익률(%)": st.column_config.NumberColumn("수익률 (%)", help="토스에서 보이는 총 수익률", format="%.1f", width="small"),
        },
        key=f"holdings_editor_{editor_ver}",
    )
    if st.button("표 초기화 (컬럼이 사라졌거나 꼬였을 때)"):
        st.session_state.pop("holdings_df", None)
        st.session_state["editor_ver"] = editor_ver + 1
        st.rerun()

    if st.button("전체 분석", type="primary"):
        records = edited.to_dict("records")
        valid = [(str(r.get("티커", "")).strip().upper(), r.get("수익률(%)")) for r in records if str(r.get("티커", "")).strip()]
        if not valid:
            st.warning("종목을 입력해주세요.")
            st.stop()
        results = []
        progress = st.progress(0, text="분석 중...")
        for i, (ticker, ret) in enumerate(valid):
            try:
                ret_val = float(ret) if ret is not None and str(ret) != "nan" else None
            except (ValueError, TypeError):
                ret_val = None
            try:
                r = score_stock(ticker, ret_val)
                r["user_return_pct"] = ret_val
                results.append(r)
            except Exception as e:
                results.append({"ticker": ticker, "name": ticker, "error": str(e)})
            progress.progress((i + 1) / len(valid), text=f"{ticker} 분석 완료")
        progress.empty()
        st.session_state["results"] = results
        st.session_state["my_tickers"] = [r["ticker"] for r in results if "error" not in r]
        st.session_state.pop("pf_diag", None)  # 새 분석이면 진단도 다시

    def total_score(r):
        return ((r.get("profit_score") or 0) + (r.get("stability_score") or 0)) / 2

    if "results" in st.session_state:
        results = st.session_state["results"]
        ok = [r for r in results if "error" not in r]
        failed = [r for r in results if "error" in r]
        ok.sort(key=total_score, reverse=True)

        if ok:
            avg_p = round(sum(r.get("profit_score") or 0 for r in ok) / len(ok))
            avg_s = round(sum(r.get("stability_score") or 0 for r in ok) / len(ok))
            c1, c2, c3 = st.columns(3)
            c1.metric("분석 종목 수", f"{len(ok)}개")
            c2.metric("평균 수익성", f"{avg_p} / 100")
            c3.metric("평균 안정성", f"{avg_s} / 100")

            # 수익률 요약 (입력된 수익률 기준)
            rets = [r.get("user_return_pct") for r in ok if r.get("user_return_pct") is not None]
            if rets:
                avg_ret = sum(rets) / len(rets)
                plus_cnt = sum(1 for x in rets if x > 0)
                minus_cnt = sum(1 for x in rets if x < 0)
                d1, d2, d3 = st.columns(3)
                ret_color = "🔴" if avg_ret > 0 else ("🔵" if avg_ret < 0 else "⚪")
                d1.metric("평균 수익률", f"{avg_ret:+.1f}%",
                          help="입력한 종목들의 수익률 평균이에요. (투자 금액 차이는 반영 안 됨)")
                d2.metric("수익 종목", f"{plus_cnt}개", help="플러스(+) 수익을 낸 종목 수")
                d3.metric("손실 종목", f"{minus_cnt}개", help="마이너스(-) 손실을 본 종목 수")
                st.caption(f"💡 입력한 {len(rets)}개 종목 중 {plus_cnt}개가 플러스, {minus_cnt}개가 마이너스예요. "
                           f"평균적으로 {abs(avg_ret):.1f}% {'수익' if avg_ret > 0 else '손실'} 상태입니다. "
                           "(각 종목에 얼마씩 넣었는지는 반영되지 않은 단순 평균이에요.)")
            st.divider()

            # ── (1) 포트폴리오 한 줄 진단 (AI) ──────────────
            if api_key:
                if st.button("🩺 내 포트폴리오 진단받기 (AI 한 줄 평)"):
                    sec_counts = {}
                    for r in ok:
                        s = r.get("sector") or "기타/미분류"
                        sec_counts[s] = sec_counts.get(s, 0) + 1
                    summary = {
                        "avg_profit": avg_p, "avg_stability": avg_s,
                        "avg_return": (sum(rets) / len(rets)) if rets else None,
                        "sectors": sorted(sec_counts.items(), key=lambda x: x[1], reverse=True),
                        "stocks": [(clean_name(r["name"]), round(total_score(r))) for r in ok],
                    }
                    with st.spinner("AI가 포트폴리오 성격을 진단 중…"):
                        st.session_state["pf_diag"] = diagnose_portfolio(summary)
                if "pf_diag" in st.session_state:
                    ai_text_box(st.session_state["pf_diag"], tone="purple")

            # ── (2) 업종(섹터) 분포 ─────────────────────────
            sec_counts = {}
            for r in ok:
                s = r.get("sector") or "기타/미분류"
                sec_counts[s] = sec_counts.get(s, 0) + 1
            if sec_counts:
                st.markdown("<div style='font-weight:600;color:#E5E2FF;margin:16px 0 6px'>업종 분포</div>", unsafe_allow_html=True)
                total_n = sum(sec_counts.values())
                palette = ["#7F77DD", "#5DCAA5", "#F0997B", "#9BC4FF", "#EF9F27", "#C77DFF", "#5BC0BE", "#E8896B"]
                for i, (sec, cnt) in enumerate(sorted(sec_counts.items(), key=lambda x: x[1], reverse=True)):
                    pct = cnt / total_n * 100
                    color = palette[i % len(palette)]
                    st.markdown(
                        f"<div style='margin:4px 0'>"
                        f"<div style='display:flex;justify-content:space-between;font-size:13px;color:#C5C9E8;margin-bottom:2px'>"
                        f"<span>{sec}</span><span>{cnt}종목 ({pct:.0f}%)</span></div>"
                        f"<div style='background:rgba(255,255,255,0.06);border-radius:5px;height:9px'>"
                        f"<div style='width:{pct}%;height:100%;background:{color};border-radius:5px'></div></div></div>",
                        unsafe_allow_html=True)
                if len(sec_counts) == 1:
                    pass  # 아래 쏠림 점검에서 함께 안내
                # ── 쏠림(집중) 점검 ──
                top_sec, top_cnt = max(sec_counts.items(), key=lambda x: x[1])
                top_pct = top_cnt / total_n * 100
                warns = []
                if len(sec_counts) == 1:
                    warns.append("모든 종목이 한 업종에 있어요. 그 업종이 흔들리면 포트폴리오 전체가 같이 흔들릴 수 있어요.")
                elif top_pct >= 50:
                    warns.append(f"'{top_sec}' 업종에 전체의 {top_pct:.0f}%가 몰려 있어요. 한 업종 쏠림이 큰 편이에요.")
                if total_n <= 3:
                    warns.append(f"종목이 {total_n}개로 적어요. 종목 수가 적으면 한 종목이 흔들릴 때 영향이 커져요.")
                if warns:
                    for w in warns:
                        st.caption(f"⚠️ {w}")
                    st.caption("💡 '분산'은 여러 업종·종목에 나눠 담아서 한 곳이 무너져도 충격을 줄이는 거예요. (강제는 아니고 참고용이에요.)")
                else:
                    st.caption("✅ 업종이 비교적 고르게 퍼져 있어요. 분산은 위험을 낮추는 투자의 기본기예요.")

            # ── (3) 목표가 도달 현황 (애널리스트 목표가 대비 현재가) ──
            reach_rows = []
            for r in ok:
                cp, tm = r.get("current_price"), r.get("target_mean")
                if cp and tm:
                    reach = cp / tm * 100  # 현재가가 목표가의 몇 %
                    reach_rows.append((clean_name(r["name"]), r["ticker"], cp, tm, reach))
            if reach_rows:
                st.markdown("<div style='font-weight:600;color:#E5E2FF;margin:18px 0 6px'>목표가 도달 현황</div>", unsafe_allow_html=True)
                st.caption("애널리스트 평균 목표주가 대비 현재가 위치예요. 100% 미만이면 목표가까지 상승 여력이, 100% 이상이면 목표가를 넘어선 상태예요.")
                reach_rows.sort(key=lambda x: x[4])
                for nm_, tkr, cp, tm, reach in reach_rows:
                    bar_w = max(0, min(100, reach))   # 막대는 0~100%로 시각화
                    over = reach >= 100
                    color = "#F0997B" if over else "#5DCAA5"
                    note = "목표가 초과" if over else f"여력 {100-reach:.0f}%"
                    st.markdown(
                        f"<div style='margin:5px 0'>"
                        f"<div style='display:flex;justify-content:space-between;font-size:13px;color:#C5C9E8;margin-bottom:2px'>"
                        f"<span>{nm_} <span style='color:#8a90bf'>({tkr})</span></span>"
                        f"<span>{reach:.0f}% · {note}</span></div>"
                        f"<div style='background:rgba(255,255,255,0.06);border-radius:5px;height:9px'>"
                        f"<div style='width:{bar_w}%;height:100%;background:{color};border-radius:5px'></div></div></div>",
                        unsafe_allow_html=True)

            # ── (3.5) 다가오는 실적 발표 일정 ──────────────
            import datetime as _dt
            _today = _dt.date.today()
            earn_rows = []
            for r in ok:
                ed = r.get("earnings_date")
                if not ed:
                    continue
                try:
                    d = _dt.datetime.strptime(ed, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if d >= _today:
                    earn_rows.append((d, clean_name(r["name"]), r["ticker"]))
            if earn_rows:
                earn_rows.sort(key=lambda x: x[0])
                st.markdown("<div style='font-weight:600;color:#E5E2FF;margin:18px 0 6px'>다가오는 실적 발표 일정</div>", unsafe_allow_html=True)
                st.caption("실적 발표 전후엔 주가가 크게 출렁일 수 있어요. 미리 알아두면 마음의 준비가 돼요. (예상 일정이라 바뀔 수 있어요.)")
                for d, nm_, tkr in earn_rows[:12]:
                    dd = (d - _today).days
                    when = "오늘" if dd == 0 else (f"{dd}일 뒤" if dd <= 45 else "예정")
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;font-size:13px;color:#C5C9E8;"
                        f"margin:3px 0;border-bottom:1px solid rgba(255,255,255,0.05);padding-bottom:3px'>"
                        f"<span>{nm_} <span style='color:#8a90bf'>({tkr})</span></span>"
                        f"<span style='color:#AFA9EC'>{d.strftime('%Y-%m-%d')} · {when}</span></div>",
                        unsafe_allow_html=True)

            # ── (4) 분석 결과 CSV 내보내기 ──────────────────
            export_rows = []
            for r in ok:
                export_rows.append({
                    "티커": r["ticker"], "종목명": clean_name(r["name"]),
                    "종합점수": round(total_score(r)),
                    "수익성": r.get("profit_score"), "안정성": r.get("stability_score"),
                    "업종": r.get("sector"), "PER": r.get("per"),
                    "현재가($)": r.get("current_price"), "목표가($)": r.get("target_mean"),
                    "상승여력(%)": r.get("upside_pct"), "수익률(%)": r.get("user_return_pct"),
                    "배당수익률(%)": r.get("dividend_yield"), "52주위치(%)": r.get("week52_pos"),
                })
            if export_rows:
                import pandas as pd
                csv_bytes = pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8-sig")
                st.download_button("📥 분석 결과 CSV로 저장", data=csv_bytes,
                                   file_name="portfolio_analysis.csv", mime="text/csv")

            st.divider()

        st.subheader("종목별 점수 (높은 순)")
        for idx, r in enumerate(ok):
            tag = "ETF" if r.get("is_etf") else "개별주"
            total = round(total_score(r))
            name = clean_name(r["name"])
            exp_key = f"explain_{r['ticker']}_{idx}"
            sum_key = f"newsum_{r['ticker']}_{idx}"
            insum_key = f"inssum_{r['ticker']}_{idx}"
            # 본 항목들을 제목 옆에 나란히 체크 표시
            badges = []
            if exp_key in st.session_state: badges.append("AI")
            if sum_key in st.session_state: badges.append("뉴스")
            if insum_key in st.session_state: badges.append("내부자")
            seen_badge = ("  ✅ " + "·".join(badges)) if badges else ""
            with st.expander(f"{name}  ·  {tag}  ·  종합 {total}점{seen_badge}"):
                m1, m2 = st.columns(2)
                m1.metric("수익성", f"{r.get('profit_score', '—')} / 100")
                m2.metric("안정성", f"{r.get('stability_score', '—')} / 100")
                details = []
                if "per" in r: details.append(f"PER {r['per']}")
                if "volatility" in r: details.append(f"변동성 {r['volatility']}")
                if "debt_to_equity" in r: details.append(f"부채비율 {r['debt_to_equity']}")
                if "upside_pct" in r: details.append(f"상승여력 {r['upside_pct']}%")
                if details:
                    st.caption("  ·  ".join(details))

                if r.get("analyst_rec") or r.get("target_mean"):
                    a_lines = []
                    if r.get("analyst_rec"):
                        cnt = f" ({r['analyst_count']}명)" if r.get("analyst_count") else ""
                        a_lines.append(f"투자의견: {r['analyst_rec']}{cnt}")
                    if r.get("target_mean"):
                        tline = f"목표주가 평균: ${r['target_mean']} <span style='color:#8a90bf;font-size:12px'>(향후 12개월 기준)</span>"
                        if r.get("target_low") and r.get("target_high"):
                            tline += f"<br><span style='color:#8a90bf'>최저 ${r['target_low']} ~ 최고 ${r['target_high']}</span>"
                        a_lines.append(tline)
                    if r.get("current_price"):
                        a_lines.append(f"현재가: ${r['current_price']}")
                    joined = "<br>".join(a_lines)
                    st.markdown(
                        f"<div style='font-weight:500;color:#E5E2FF;margin-bottom:6px'>애널리스트 의견</div>"
                        f"<div style='color:#C5C9E8;font-size:14px;line-height:1.8'>{joined}</div>",
                        unsafe_allow_html=True)

                btn_label = "AI 설명 다시 보기" if exp_key in st.session_state else "AI 설명 보기"
                if st.button(btn_label, key=f"btn_{exp_key}"):
                    if not api_key:
                        st.warning("왼쪽 사이드바에 Gemini API 키를 먼저 넣어주세요.")
                    else:
                        with st.spinner("AI가 설명을 작성 중..."):
                            st.session_state[exp_key] = explain_stock(r)
                            st.rerun()
                if exp_key in st.session_state:
                    ai_text_box(st.session_state[exp_key], tone="purple")

                # 최신 뉴스
                sum_key = f"newsum_{r['ticker']}_{idx}"
                st.markdown(f"<div style='font-weight:600;color:#E5E2FF;margin-top:14px;font-size:15px'>최신 뉴스</div>", unsafe_allow_html=True)
                news_items = get_news(r["ticker"], limit=10)
                if news_items:
                    nsum_label = "뉴스 요약 다시 보기" if sum_key in st.session_state else "뉴스 핵심 요약"
                    if st.button(nsum_label, key=f"sumbtn_{sum_key}"):
                        if not api_key:
                            st.warning("왼쪽 사이드바에 Gemini API 키를 먼저 넣어주세요.")
                        else:
                            with st.spinner("AI가 뉴스를 요약 중..."):
                                st.session_state[sum_key] = summarize_news(clean_name(r["name"]), news_items, r["ticker"])
                                st.rerun()
                    if sum_key in st.session_state:
                        ai_text_box(st.session_state[sum_key], tone="purple")

                    with st.expander(f"뉴스 전체 보기 ({len(news_items)}건)"):
                        for n in news_items:
                            meta = " · ".join(x for x in [n["publisher"], n["time"]] if x)
                            if n["link"]:
                                st.markdown(f"- [{n['title']}]({n['link']})  \n<span style='color:#8a90bf;font-size:12px'>{meta}</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"- {n['title']}  \n<span style='color:#8a90bf;font-size:12px'>{meta}</span>", unsafe_allow_html=True)
                else:
                    st.caption("관련 뉴스를 찾지 못했어요.")

                if not r.get("is_etf"):
                    ins_key = f"insider_{r['ticker']}_{idx}"
                    insum_key = f"inssum_{r['ticker']}_{idx}"
                    st.markdown(f"<div style='font-weight:600;color:#E5E2FF;margin-top:14px;font-size:15px'>내부자 거래 (임원·이사)</div>", unsafe_allow_html=True)
                    if st.button("내부자 거래 보기", key=f"insbtn_{ins_key}"):
                        with st.spinner("SEC에서 내부자 거래를 불러오는 중..."):
                            st.session_state[ins_key] = get_insider_trades(r["ticker"], limit=8)
                            st.rerun()
                    if ins_key in st.session_state:
                        trades = st.session_state[ins_key]
                        if not trades:
                            st.caption("최근 내부자 거래 기록이 없어요.")
                        else:
                            insum_label = "내부자 요약 다시 보기" if insum_key in st.session_state else "내부자 거래 핵심 요약"
                            if st.button(insum_label, key=f"inssumbtn_{insum_key}"):
                                if not api_key:
                                    st.warning("왼쪽 사이드바에 Gemini API 키를 먼저 넣어주세요.")
                                else:
                                    with st.spinner("AI가 내부자 거래를 요약 중..."):
                                        st.session_state[insum_key] = summarize_insider(clean_name(r["name"]), trades)
                                        st.rerun()
                            if insum_key in st.session_state:
                                ai_text_box(st.session_state[insum_key], tone="purple")

                            with st.expander(f"내부자 거래 전체 보기 ({len(trades)}건)"):
                                rows_html = ""
                                for t in trades:
                                    for tx in t["txns"]:
                                        if tx["kind"] == "buy":
                                            color = "#9FE1CB"
                                        elif tx["kind"] == "sell":
                                            color = "#F0997B"
                                        else:
                                            color = "#AFA9EC"
                                        sh = f"{tx['shares']:,}주" if tx["shares"] else ""
                                        pr = f" @ ${tx['price']}" if tx["price"] else ""
                                        rows_html += (
                                            f"<div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:0.5px solid rgba(175,169,236,0.15)'>"
                                            f"<span style='color:#C5C9E8;font-size:13px'>{t['date']} · {t['name']} <span style='color:#8a90bf'>({t['title']})</span></span>"
                                            f"<span style='color:{color};font-size:13px;font-weight:500'>{tx['label']} {sh}{pr}</span></div>"
                                        )
                                st.markdown(f"<div style='margin-top:4px'>{rows_html}</div>", unsafe_allow_html=True)
                                st.caption("초록=매수성격 · 빨강=매도성격 · 보라=중립(보상·증여 등)")

        if failed:
            st.divider()
            st.warning("불러오지 못한 종목: " + ", ".join(r["ticker"] for r in failed))

elif page == "부자들은 요즘 뭘 샀나":
    st.markdown(
        "<div style='border-bottom:1px solid rgba(175,169,236,0.2);padding-bottom:14px;margin-bottom:18px'>"
        "<div style='font-size:28px;font-weight:700;font-family:Orbitron,sans-serif;color:#F4F5FF;letter-spacing:0.5px;text-shadow:0 0 18px rgba(127,119,221,0.5)'>SMART MONEY TRACKER</div>"
        "<div style='color:#9BA0C4;font-size:14px;margin-top:4px'>유명 투자자·기관이 SEC에 보고한 최신 보유 종목(13F)입니다. 법규상 분기 종료 후 약 45일 뒤 공개되어 실시간은 아닙니다.</div>"
        "</div>",
        unsafe_allow_html=True)

    # ── 스마트머니 인기종목 랭킹 (여러 큰손이 공통으로 담은 종목) ──
    with st.expander("🏆 스마트머니 인기종목 — 여러 큰손이 공통으로 담은 종목"):
        st.caption(f"등록된 유명 투자자 {len(SUPER_INVESTORS)}명의 최신 13F 상위 보유 종목을 모아, "
                   "여러 명이 겹쳐서 담은 종목을 순위로 보여줘요. (보유 투자자 수 기준)")
        if st.button("랭킹 계산하기", key="smr_btn"):
            with st.spinner(f"{len(SUPER_INVESTORS)}명의 13F를 SEC에서 모아 집계 중… (처음엔 좀 걸려요)"):
                st.session_state["smr"] = compute_smart_money_ranking()

        smr = st.session_state.get("smr")
        if smr is not None:
            shared = [x for x in smr if x["count"] >= 2][:20]
            if not shared:
                st.info("2명 이상이 공통으로 담은 종목을 찾지 못했어요. (데이터를 못 불러왔을 수 있어요)")
            else:
                max_cnt = shared[0]["count"]
                my_tickers = set(st.session_state.get("my_tickers", []))
                for rank, x in enumerate(shared, 1):
                    tk = x["ticker"]
                    tk_disp = f" <span style='color:#8a90bf;font-size:12px'>({tk})</span>" if tk else ""
                    mine = tk and tk in my_tickers
                    mine_disp = " <span style='color:#5DCAA5;font-size:11px'>· 내 보유</span>" if mine else ""
                    holders = [n.split(" (")[0] for n in x["holders"]]
                    hd = ", ".join(holders[:4]) + (f" 외 {len(holders)-4}명" if len(holders) > 4 else "")
                    val_disp = f"${x['total_value']/1e9:,.1f}B" if x["total_value"] >= 1e9 else f"${x['total_value']/1e6:,.0f}M"
                    bar_w = int(x["count"] / max_cnt * 100) if max_cnt else 0
                    st.markdown(
                        f"<div style='padding:8px 2px;border-bottom:1px solid rgba(175,169,236,0.08)'>"
                        f"<div style='display:flex;justify-content:space-between;align-items:baseline'>"
                        f"<span style='color:#E5E2FF;font-size:14px;font-weight:500'>{rank}. {x['name'].title()}{tk_disp}{mine_disp}</span>"
                        f"<span style='color:#AFA9EC;font-size:13px;font-weight:600;white-space:nowrap'>{x['count']}명 · {val_disp}</span></div>"
                        f"<div style='background:rgba(255,255,255,0.06);border-radius:4px;height:6px;margin:5px 0 4px'>"
                        f"<div style='width:{bar_w}%;height:100%;background:#7F77DD;border-radius:4px'></div></div>"
                        f"<div style='color:#8a90bf;font-size:11px'>{hd}</div></div>",
                        unsafe_allow_html=True)
                st.caption("여러 큰손이 겹쳐 담을수록 위에 표시돼요. 13F는 분기 후 약 45일 뒤 공시라 실시간이 아니며, 투자 추천이 아닙니다.")

                # ── 종목 하나 깊게: 왜 보유 + 전망 (클릭하면 로딩) ──
                if api_key:
                    opts = {}
                    for x in shared:
                        if x.get("ticker"):
                            label = f"{x['name'].title()} ({x['ticker']})"
                            opts[label] = x
                    if opts:
                        st.markdown("<div style='margin-top:12px;font-weight:600;color:#E5E2FF'>🔍 이 중 한 종목, 큰손들이 왜 들고 있는지 + 전망 보기</div>", unsafe_allow_html=True)
                        pick_label = st.selectbox("종목 선택", ["(고르기)"] + list(opts.keys()),
                                                  key="smr_thesis_pick", label_visibility="collapsed")
                        if st.button("왜 보유 + 전망 분석", key="smr_thesis_btn"):
                            if pick_label == "(고르기)":
                                st.warning("먼저 종목을 골라주세요.")
                            else:
                                x = opts[pick_label]
                                with st.spinner(f"{x['name'].title()}의 데이터·뉴스·전망을 모으는 중… (10~30초)"):
                                    try:
                                        _sc = score_stock(x["ticker"], None)
                                    except Exception:
                                        _sc = None
                                    _nw = get_news(x["ticker"], limit=5)
                                    _holders = [n.split(" (")[0] for n in x["holders"]]
                                    _th, _therr = analyze_holding_thesis(
                                        x["name"].title(), x["ticker"], _holders, _sc, _nw)
                                st.session_state["smr_thesis"] = (pick_label, _th, _therr)
                        th_state = st.session_state.get("smr_thesis")
                        if th_state:
                            tlabel, th, therr = th_state
                            if therr:
                                st.error(therr)
                            elif th:
                                st.markdown(
                                    f"<div style='font-weight:700;color:#F4F5FF;margin:10px 0 4px'>🔍 {tlabel}</div>",
                                    unsafe_allow_html=True)
                                ai_text_box(th.get("text", ""), tone="green")
                                policy_sources_expander(th)
                                st.caption("큰손이 샀다고 좋은 종목이라는 뜻은 아니에요. 13F는 분기 뒤 공시라 지금은 다를 수 있어요.")

    # ── 두 투자자 포트폴리오 비교 ──────────────────────────
    with st.expander("🆚 두 투자자 포트폴리오 비교"):
        names_list = list(SUPER_INVESTORS.keys())
        cc1, cc2 = st.columns(2)
        inv_a = cc1.selectbox("투자자 A", names_list, key="cmp_inv_a")
        inv_b = cc2.selectbox("투자자 B", names_list,
                              index=1 if len(names_list) > 1 else 0, key="cmp_inv_b")
        if st.button("두 투자자 비교하기", key="cmp_inv_btn"):
            if inv_a == inv_b:
                st.warning("서로 다른 투자자를 골라주세요.")
            else:
                with st.spinner("두 투자자의 13F를 불러오는 중…"):
                    rda, ha = get_13f_holdings(SUPER_INVESTORS[inv_a], 15)
                    rdb, hb = get_13f_holdings(SUPER_INVESTORS[inv_b], 15)
                st.session_state["cmp_inv"] = {"a": (inv_a, rda, ha), "b": (inv_b, rdb, hb)}

        ci = st.session_state.get("cmp_inv")
        if ci:
            (na, rda, ha), (nb, rdb, hb) = ci["a"], ci["b"]
            if not ha or not hb:
                st.info("두 투자자 중 한 명의 보유 종목을 불러오지 못했어요.")
            else:
                # 티커로 매핑 (공통 종목 찾기용)
                def _tkmap(hs):
                    d = {}
                    for h in hs:
                        k = guess_ticker(h["name"]) or h["name"].upper()
                        d[k] = h
                    return d
                ma, mb = _tkmap(ha), _tkmap(hb)
                common = set(ma) & set(mb)

                if common:
                    names = []
                    for k in common:
                        tkd = f" ({k})" if not k.isupper() or len(k) <= 5 else ""
                        names.append(f"{ma[k]['name'].title()}{tkd}")
                    st.markdown(
                        f"<div style='background:rgba(159,225,203,0.10);border-left:3px solid #5DCAA5;"
                        f"border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:10px;color:#E5E2FF;font-size:13px'>"
                        f"<span style='color:#9FE1CB;font-weight:600'>두 사람 모두 보유</span> &nbsp;"
                        f"{', '.join(names[:8])}{(' 외 ' + str(len(common)-8) + '종목') if len(common) > 8 else ''}</div>",
                        unsafe_allow_html=True)
                else:
                    st.caption("상위 보유 종목 중 겹치는 종목은 없어요.")

                colx, coly = st.columns(2)
                for col, (nm_, hs) in [(colx, (na, ha)), (coly, (nb, hb))]:
                    tot = sum(h["value"] for h in hs) or 1
                    with col:
                        st.markdown(
                            f"<div style='font-weight:700;color:#F4F5FF;font-size:14px;margin-bottom:6px'>"
                            f"{nm_.split(' (')[0]}</div>", unsafe_allow_html=True)
                        for h in hs[:12]:
                            k = guess_ticker(h["name"]) or h["name"].upper()
                            shared = k in common
                            mark = "🔗 " if shared else ""
                            col_txt = "#9FE1CB" if shared else "#C5C9E8"
                            w = h["value"] / tot * 100
                            st.markdown(
                                f"<div style='display:flex;justify-content:space-between;font-size:12px;"
                                f"padding:3px 0;border-bottom:1px solid rgba(175,169,236,0.06)'>"
                                f"<span style='color:{col_txt};white-space:nowrap;overflow:hidden;"
                                f"text-overflow:ellipsis;max-width:70%'>{mark}{h['name'].title()}</span>"
                                f"<span style='color:#8a90bf'>{w:.1f}%</span></div>",
                                unsafe_allow_html=True)
                st.caption("🔗 표시는 두 사람이 공통으로 담은 종목이에요. 상위 12개씩, 비중은 신고 자산 대비예요.")

    inv_name = st.selectbox("투자자 / 기관 선택", list(SUPER_INVESTORS.keys()))
    if st.button("보유 종목 보기", type="primary"):
        cik = SUPER_INVESTORS[inv_name]
        import yfinance as yf
        with st.spinner(f"SEC에서 {inv_name}의 13F를 불러오는 중..."):
            report_date, holdings = get_13f_holdings(cik)
        # 시총·티커를 여기서 한 번만 계산해서 저장 (이후 클릭마다 재계산 안 함)
        if holdings:
            total_val = sum(h["value"] for h in holdings)
            with st.spinner("종목별 시가총액·티커 확인 중... (잠시만요)"):
                for h in holdings:
                    h["_ticker"] = guess_ticker(h["name"])
                    h["_weight"] = h["value"] / total_val * 100 if total_val else 0
                    h["_mcap"] = None
                    h["_price"] = None
                    if h["_ticker"]:
                        try:
                            info = yf.Ticker(h["_ticker"]).info
                            h["_mcap"] = info.get("marketCap")
                            h["_price"] = info.get("currentPrice") or info.get("regularMarketPrice")
                        except Exception:
                            pass
        st.session_state["si_result"] = (inv_name, report_date, holdings)
        for k in ("si_ai", "si_small_ai", "si_show_all", "si_page", "si_open_stock", "si_stock_ai", "cmp13f"):
            st.session_state.pop(k, None)

    if "si_result" in st.session_state:
        nm, rd, holdings = st.session_state["si_result"]

        # 오래된 보고서 판단 (기준일이 약 8개월 이상 지났으면 최신 아님)
        stale = False
        try:
            from datetime import date
            y, m, d = map(int, rd.split("-"))
            months_old = (date.today().year - y) * 12 + (date.today().month - m)
            stale = months_old > 8
        except Exception:
            pass

        if not holdings:
            st.warning("보유 종목을 불러오지 못했습니다.")
        elif stale:
            st.warning(f"이 투자자의 가장 최근 공시는 {rd} 기준으로, 최신 분기 데이터가 아닙니다. 13F 보고를 중단했거나 지연된 경우라 표시하지 않습니다.")
        else:
            total_val = sum(h["value"] for h in holdings)
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:10px;margin:14px 0 4px'>"
                f"<span style='font-size:17px;font-weight:500;color:#F4F5FF'>{nm}</span>"
                f"<span style='background:rgba(175,169,236,0.15);color:#AFA9EC;font-size:12px;padding:3px 10px;border-radius:6px'>기준일 {rd}</span></div>",
                unsafe_allow_html=True)
            st.markdown(
                f"<div style='color:#8a90bf;font-size:13px;margin-bottom:14px'>보유 종목 {len(holdings)}개 · 신고 자산 총액 약 ${total_val/1e9:,.1f}B</div>",
                unsafe_allow_html=True)

            # ── 직전 분기 대비 변화 (신규매수·전량매도·비중확대·축소) ──
            with st.expander("📊 직전 분기 대비 무엇이 바뀌었나 (신규 매수·전량 매도)"):
                st.caption("이전 분기 13F 보고서와 비교해 새로 사고 판 종목을 정리해요. (보유 주식 수 기준)")
                if st.button("변화 분석하기", key="cmp13f_btn"):
                    cik = SUPER_INVESTORS.get(nm)
                    if not cik:
                        st.session_state["cmp13f"] = {"ok": False, "reason": "이 투자자의 CIK를 찾지 못했어요."}
                    else:
                        with st.spinner("이전 분기 보고서를 SEC에서 가져와 비교 중…"):
                            st.session_state["cmp13f"] = get_13f_comparison(cik)

                cmp = st.session_state.get("cmp13f")
                if cmp:
                    if not cmp.get("ok"):
                        st.info(cmp.get("reason", "비교 데이터를 가져오지 못했어요."))
                    else:
                        st.markdown(
                            f"<div style='color:#9BA0C4;font-size:13px;margin:4px 0 10px'>"
                            f"<span style='color:#AFA9EC'>{cmp['prev_date']}</span> → "
                            f"<span style='color:#AFA9EC'>{cmp['latest_date']}</span> 비교 · 보유 주식 수 기준</div>",
                            unsafe_allow_html=True)

                        def _cmp_block(title, items, color, emoji, show_chg=False):
                            if not items:
                                return
                            st.markdown(
                                f"<div style='font-weight:600;color:{color};margin:10px 0 4px'>{emoji} {title} "
                                f"<span style='color:#8a90bf;font-weight:400'>({len(items)}종목)</span></div>",
                                unsafe_allow_html=True)
                            for it in items[:10]:
                                tk = guess_ticker(it["name"]) or ""
                                tk_disp = f" <span style='color:#8a90bf'>({tk})</span>" if tk else ""
                                val_disp = f"${it['value']/1e6:,.0f}M" if it.get("value") else ""
                                chg_disp = ""
                                if show_chg and it.get("change_pct") is not None:
                                    sign = "+" if it["change_pct"] > 0 else ""
                                    chg_disp = f" · 주식 수 {sign}{it['change_pct']}%"
                                st.markdown(
                                    f"<div style='display:flex;justify-content:space-between;"
                                    f"border-bottom:1px solid rgba(175,169,236,0.08);padding:5px 2px;font-size:13px'>"
                                    f"<span style='color:#E5E2FF'>{it['name'].title()}{tk_disp}</span>"
                                    f"<span style='color:#9BA0C4'>{val_disp}{chg_disp}</span></div>",
                                    unsafe_allow_html=True)
                            if len(items) > 10:
                                st.caption(f"…외 {len(items)-10}종목")

                        any_change = any([cmp["new"], cmp["exited"], cmp["increased"], cmp["decreased"]])
                        if not any_change:
                            st.info("직전 분기와 비교해 눈에 띄는 변화가 없어요.")
                        else:
                            _cmp_block("새로 산 종목 (신규 매수)", cmp["new"], "#5DCAA5", "🟢")
                            _cmp_block("전부 판 종목 (전량 매도)", cmp["exited"], "#E8896B", "🔴")
                            _cmp_block("비중 늘린 종목", cmp["increased"], "#9FE1CB", "▲", show_chg=True)
                            _cmp_block("비중 줄인 종목", cmp["decreased"], "#F0B27B", "▼", show_chg=True)
                        st.caption("13F는 분기 종료 후 최대 45일 뒤 공시되어, 현재 보유와 다를 수 있어요.")

            # 시총은 이미 저장됨. 겹침/소형주 판단만 (네트워크 호출 없음)
            import yfinance as yf
            from superinvestor_fetch import classify_size
            my_tickers = set(st.session_state.get("my_tickers", []))
            overlaps = []
            small_bets = []
            for h in holdings:
                if h.get("_mcap") and h["_mcap"] < 10e9 and h.get("_weight", 0) >= 5:
                    small_bets.append(h)

            # 내 종목 겹침
            if my_tickers:
                overlap_holdings = []
                for h in holdings:
                    if h["_ticker"] and h["_ticker"] in my_tickers:
                        overlaps.append((h["name"], h["_ticker"]))
                        overlap_holdings.append(h)
                if overlaps:
                    ov = ", ".join(f"{n} ({t})" for n, t in overlaps)
                    st.markdown(
                        f"<div style='background:rgba(159,225,203,0.10);border-left:3px solid #5DCAA5;border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:6px;color:#E5E2FF;font-size:14px'>"
                        f"<span style='color:#9FE1CB;font-weight:600'>나와 겹치는 종목</span> &nbsp;{ov}</div>",
                        unsafe_allow_html=True)
                    # 겹치는 종목별 상세 (이 투자자의 비중 + 내 수익률)
                    my_returns = {}
                    for rr in st.session_state.get("results", []):
                        if "error" not in rr and rr.get("user_return_pct") is not None:
                            my_returns[rr["ticker"]] = rr["user_return_pct"]
                    cards = ""
                    for h in overlap_holdings:
                        tk = h["_ticker"]
                        their_w = h["_weight"]
                        my_r = my_returns.get(tk)
                        kr = ""
                        try:
                            from stock_search import korean_name
                            kr = korean_name(tk) or ""
                        except Exception:
                            pass
                        name_disp = f"{kr} ({tk})" if kr else f"{h['name']} ({tk})"
                        my_part = ""
                        if my_r is not None:
                            rc = "#9FE1CB" if my_r > 0 else "#F0997B" if my_r < 0 else "#AFA9EC"
                            my_part = f"<span style='color:{rc}'>내 수익률 {my_r:+.1f}%</span>"
                        cards += (
                            f"<div style='display:flex;justify-content:space-between;align-items:center;"
                            f"background:rgba(159,225,203,0.05);border-radius:8px;padding:9px 14px;margin:4px 0;font-size:13px'>"
                            f"<span style='color:#E5E2FF;font-weight:500'>{name_disp}</span>"
                            f"<span style='color:#C5C9E8'>이 투자자 비중 {their_w:.1f}% &nbsp;·&nbsp; {my_part}</span></div>"
                        )
                    st.markdown(f"<div style='margin-bottom:14px'>{cards}</div>", unsafe_allow_html=True)

            # 이 투자자가 보유한 소형주/중형주 정리 (규모별 발굴 종목)
            small_caps = []
            mid_caps = []
            for h in holdings:
                if h.get("_mcap"):
                    if h["_mcap"] < 2e9:
                        small_caps.append(h)
                    elif h["_mcap"] < 10e9:
                        mid_caps.append(h)
            if small_caps or mid_caps:
                def _cap_rows(lst, emoji, label, color):
                    if not lst:
                        return ""
                    lst_sorted = sorted(lst, key=lambda x: x["_weight"], reverse=True)
                    rows = ""
                    for h in lst_sorted[:8]:
                        rows += (f"<div style='display:flex;justify-content:space-between;padding:5px 0;font-size:13px'>"
                                 f"<span style='color:#E5E2FF'>{h['name']}</span>"
                                 f"<span style='color:#8a90bf'>비중 {h['_weight']:.1f}% · 시총 ${h['_mcap']/1e9:.1f}B</span></div>")
                    more = f"<div style='color:#8a90bf;font-size:12px;margin-top:4px'>외 {len(lst)-8}개 더</div>" if len(lst) > 8 else ""
                    return (f"<div style='margin-bottom:8px'><div style='color:{color};font-weight:600;font-size:13px;margin-bottom:2px'>{emoji} {label} ({len(lst)}개)</div>{rows}{more}</div>")
                body = _cap_rows(small_caps, "🔴", "소형주 (시총 20억 달러 미만)", "#F0997B") + _cap_rows(mid_caps, "🟠", "중형주 (시총 100억 달러 미만)", "#EF9F27")
                st.markdown(
                    f"<div style='background:rgba(127,119,221,0.06);border:0.5px solid rgba(175,169,236,0.2);border-radius:10px;padding:12px 16px;margin-bottom:14px'>"
                    f"<div style='color:#C5C9E8;font-size:12px;margin-bottom:8px'>이 투자자가 보유한 중소형주예요. 대형주보다 변동성이 크지만 발굴형 베팅일 수 있어요.</div>"
                    f"{body}</div>",
                    unsafe_allow_html=True)

            # 작은 회사 집중 매수
            if small_bets:
                items = ""
                for h in small_bets:
                    size, scolor = classify_size(h["_mcap"])
                    items += (f"<div style='margin:5px 0;color:#E5E2FF;font-size:14px'>"
                              f"<span style='font-weight:500'>{h['name']}</span> "
                              f"<span style='color:#8a90bf'>· 비중 {h['_weight']:.1f}% · 시총 ${h['_mcap']/1e9:.1f}B</span> "
                              f"<span style='color:{scolor};font-size:12px'>{size}</span></div>")
                st.markdown(
                    f"<div style='background:rgba(240,153,123,0.10);border-left:3px solid #D85A30;border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:6px'>"
                    f"<div style='color:#F0997B;font-weight:500;margin-bottom:4px'>작은 회사 집중 매수</div>"
                    f"<div style='color:#8a90bf;font-size:12px;margin-bottom:6px'>시가총액이 작은데 포트폴리오 비중이 큰 종목입니다. 발굴형 베팅일 수 있습니다.</div>"
                    f"{items}</div>",
                    unsafe_allow_html=True)

                # 작은 회사를 왜 샀을지 AI 설명
                if api_key:
                    if st.button("작은 회사 매수 이유 분석"):
                        from ai_explain import _client, _friendly_error
                        sb_lines = ""
                        for h in small_bets:
                            tk = h["_ticker"]
                            heads = ""
                            if tk:
                                items_n = get_news(tk, limit=3)
                                if items_n:
                                    heads = "; ".join(n["title"] for n in items_n)
                            sb_lines += f"\n- {h['name']} (비중 {h['_weight']:.1f}%): {heads}"
                        with st.spinner("AI가 분석 중..."):
                            try:
                                prompt = (f"'{nm}' 투자자가 다음의 시가총액이 작은 회사들에 큰 비중을 실었어:{sb_lines}\n\n"
                                          "각 회사가 어떤 사업을 하는 곳인지, 그리고 이 투자자가 왜 이 작은 회사들에 주목했을지 "
                                          "뉴스 맥락을 참고해 추측해서 한국어로 4~5문장으로 쉽게 설명해줘. "
                                          "제목·번호·별표 없이 자연스러운 문단으로. 투자 추천은 하지 마.")
                                resp = _client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
                                st.session_state["si_small_ai"] = resp.text.strip()
                            except Exception as e:
                                st.session_state["si_small_ai"] = _friendly_error(e)
                    if "si_small_ai" in st.session_state:
                        ai_text_box(st.session_state["si_small_ai"], tone="orange")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # 포트폴리오 전체 AI 분석
            if api_key:
                if st.button("포트폴리오 종합 분석 (+상위 종목 뉴스)"):
                    top_names = ", ".join(h["name"] for h in holdings[:10])
                    from ai_explain import _client, _friendly_error
                    with st.spinner("AI가 상위 종목 뉴스까지 모아 분석 중..."):
                        news_ctx = ""
                        for h in holdings[:3]:
                            if h["_ticker"]:
                                items_n = get_news(h["_ticker"], limit=3)
                                if items_n:
                                    news_ctx += f"\n[{h['name']}] " + "; ".join(n["title"] for n in items_n)
                        try:
                            prompt = (f"'{nm}'의 최신 13F 상위 보유 종목: {top_names}.\n"
                                      f"상위 종목 최근 뉴스:{news_ctx}\n\n"
                                      "이 투자자의 포트폴리오 특징(집중 업종·테마, 투자 성향)과 상위 종목들의 최근 이슈를 "
                                      "한국어로 4~5문장으로 쉽게 설명해줘. 제목·번호·별표 없이 자연스러운 문단으로. 투자 추천은 하지 마.")
                            resp = _client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
                            st.session_state["si_ai"] = resp.text.strip()
                        except Exception as e:
                            st.session_state["si_ai"] = _friendly_error(e)
                if "si_ai" in st.session_state:
                    ai_text_box(st.session_state["si_ai"], tone="purple")

            # 보유 종목 목록 (15개씩 페이지 넘기기 + 종목 클릭 상세)
            st.markdown("<div style='color:#9BA0C4;font-size:13px;margin:10px 0 4px'>종목을 누르면 뉴스·데이터·AI 매수 이유를 볼 수 있습니다.</div>", unsafe_allow_html=True)
            PER_PAGE = 15
            n_pages = (len(holdings) + PER_PAGE - 1) // PER_PAGE
            page_idx = st.session_state.get("si_page", 0)
            page_idx = max(0, min(page_idx, n_pages - 1))
            start = page_idx * PER_PAGE
            page_items = holdings[start:start + PER_PAGE]

            for i, h in enumerate(page_items, start + 1):
                mine = h["_ticker"] and h["_ticker"] in my_tickers
                tags = ""
                if mine:
                    tags += " · 보유"
                if h.get("_mcap") and h["_mcap"] < 10e9:
                    size, _ = classify_size(h["_mcap"])
                    emoji = "🔴" if size == "소형주" else "🟠"
                    tags += f" · {emoji} {size}"
                # 뉴스 요약을 본 종목은 체크 표시
                tkk = h.get("_ticker")
                if tkk and f"si_newsum_{tkk}" in st.session_state:
                    tags += " · ✅뉴스"
                # 현재가는 펼침 상세에만 표시 (목록 줄에는 제외)
                # 달러기호($)는 \$로 이스케이프 — 안 하면 Streamlit이 $…$ 사이를 수식으로 잘못 렌더링함
                label = f"{i}. {h['name']}{tags}    \\${h['value']/1e6:,.0f}M ({h['_weight']:.1f}%)"
                if st.button(label, key=f"stk_{start}_{i}", use_container_width=True):
                    cur = st.session_state.get("si_open_stock")
                    st.session_state["si_open_stock"] = None if cur == h["name"] else h["name"]
                    st.rerun()

                # 종목 상세 펼침
                if st.session_state.get("si_open_stock") == h["name"]:
                    tk = h["_ticker"]
                    with st.container():
                        if not tk:
                            st.caption("이 종목은 티커 매칭에 실패해서 상세 정보를 불러올 수 없어요.")
                        else:
                            # 데이터 분석 (점수) - 종목별 캐싱
                            sd_key = f"si_data_{tk}"
                            if sd_key not in st.session_state:
                                try:
                                    st.session_state[sd_key] = score_stock(tk, None)
                                except Exception:
                                    st.session_state[sd_key] = None
                            sd = st.session_state[sd_key]
                            if sd:
                                dline = ""
                                if not sd.get("is_etf"):
                                    if sd.get("per"): dline += f"PER {sd['per']:.1f} · "
                                    if sd.get("volatility"): dline += f"변동성 {sd['volatility']:.2f} · "
                                    if sd.get("analyst_rec"): dline += f"투자의견 {sd['analyst_rec']} · "
                                    if sd.get("target_mean"): dline += f"목표주가 ${sd['target_mean']} (향후 12개월) · "
                                if sd.get("current_price"): dline += f"현재가 ${sd['current_price']}"
                                st.markdown(
                                    f"<div style='background:rgba(127,119,221,0.08);border-radius:8px;padding:10px 14px;margin:4px 0;color:#C5C9E8;font-size:13px'>"
                                    f"<b style='color:#AFA9EC'>{sd.get('name', tk)}</b> ({tk})<br>{dline.rstrip(' · ')}</div>",
                                    unsafe_allow_html=True)
                            else:
                                st.caption("데이터를 불러오지 못했어요.")

                            # 뉴스 - 종목별 캐싱
                            news_key = f"si_news_{tk}"
                            if news_key not in st.session_state:
                                st.session_state[news_key] = get_news(tk, limit=8)
                            news_items = st.session_state[news_key]
                            if news_items:
                                # 뉴스 요약 (체크 연동)
                                if api_key:
                                    newsum_key = f"si_newsum_{tk}"
                                    nsum_label = "뉴스 요약 다시 보기" if newsum_key in st.session_state else "뉴스 핵심 요약"
                                    if st.button(nsum_label, key=f"nsum_{start}_{i}"):
                                        with st.spinner("AI가 뉴스를 요약 중..."):
                                            st.session_state[newsum_key] = summarize_news(h["name"], news_items, tk)
                                            st.rerun()
                                    if newsum_key in st.session_state:
                                        ai_text_box(st.session_state[newsum_key], tone="purple")
                                with st.expander(f"최신 뉴스 ({len(news_items)}건)"):
                                    for n in news_items:
                                        meta = " · ".join(x for x in [n.get("publisher", ""), n.get("time", "")] if x)
                                        if n.get("link"):
                                            st.markdown(f"- [{n['title']}]({n['link']})  \n<span style='color:#8a90bf;font-size:12px'>{meta}</span>", unsafe_allow_html=True)
                                        else:
                                            st.markdown(f"- {n['title']}  \n<span style='color:#8a90bf;font-size:12px'>{meta}</span>", unsafe_allow_html=True)

                            # AI 매수 이유 - 종목별 키로 보존
                            if api_key:
                                why_key = f"si_why_{tk}"
                                why_label = "AI 분석 다시 보기" if why_key in st.session_state else "이 종목을 왜 샀는지 AI 분석"
                                if st.button(why_label, key=f"why_{start}_{i}"):
                                    from ai_explain import _client, _friendly_error
                                    heads = "; ".join(n["title"] for n in news_items[:4]) if news_items else ""
                                    with st.spinner("AI가 분석 중..."):
                                        try:
                                            prompt = (f"'{nm}' 투자자가 '{h['name']}'({tk}) 종목을 포트폴리오 비중 {h['_weight']:.1f}%로 보유하고 있어. "
                                                      f"이 회사의 최근 뉴스: {heads}\n\n"
                                                      "이 회사가 어떤 사업을 하는 곳인지, 그리고 이 투자자가 왜 이 종목을 샀을지 "
                                                      "뉴스 맥락을 참고해 추측해서 한국어로 3~4문장으로 쉽게 설명해줘. "
                                                      "제목·번호·별표 없이 자연스러운 문단으로. 투자 추천은 하지 마.")
                                            resp = _client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
                                            st.session_state[why_key] = resp.text.strip()
                                        except Exception as e:
                                            st.session_state[why_key] = _friendly_error(e)
                                        st.rerun()
                                if why_key in st.session_state:
                                    ai_text_box(st.session_state[why_key], tone="purple")

            # 페이지 넘기기
            if n_pages > 1:
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    if st.button("← 이전", disabled=(page_idx == 0), use_container_width=True):
                        st.session_state["si_page"] = page_idx - 1
                        st.session_state["si_open_stock"] = None
                        st.rerun()
                with c2:
                    st.markdown(f"<div style='text-align:center;color:#9BA0C4;padding-top:6px'>{page_idx+1} / {n_pages} 페이지</div>", unsafe_allow_html=True)
                with c3:
                    if st.button("다음 →", disabled=(page_idx == n_pages - 1), use_container_width=True):
                        st.session_state["si_page"] = page_idx + 1
                        st.session_state["si_open_stock"] = None
                        st.rerun()

            st.caption("13F는 미국 주식 매수 포지션만 공개됩니다. 공매도·해외주식·현금은 제외되며, 종목 매칭은 회사명 기반 추정이라 일부 부정확할 수 있습니다.")


elif page == "종목 검색":
    st.markdown(
        "<div style='border-bottom:1px solid rgba(175,169,236,0.2);padding-bottom:14px;margin-bottom:18px'>"
        "<div style='font-size:28px;font-weight:700;font-family:Orbitron,sans-serif;color:#F4F5FF;letter-spacing:0.5px;text-shadow:0 0 18px rgba(127,119,221,0.5)'>STOCK FINDER</div>"
        "<div style='color:#9BA0C4;font-size:14px;margin-top:4px'>종목 하나를 검색해 점수·차트·애널리스트·뉴스·내부자 거래·AI 분석을 한눈에 봅니다.</div>"
        "</div>",
        unsafe_allow_html=True)

    c1, c2 = st.columns([4, 1])
    with c1:
        query = st.text_input("종목 검색", placeholder="티커(AAPL) 또는 회사 이름(애플, apple)을 입력하세요",
                              label_visibility="collapsed")
    with c2:
        do_search = st.button("검색", type="primary", use_container_width=True)

    # ── 여러 종목 비교 (2~3개 나란히) ──────────────────────
    with st.expander("🆚 여러 종목 한눈에 비교하기 (2~3개)"):
        cmp_q = st.text_input("비교할 종목들",
                              placeholder="쉼표로 구분, 예: AAPL, MSFT, NVDA",
                              key="sf_cmp_input", label_visibility="collapsed")
        if st.button("비교하기", key="sf_cmp_btn"):
            raw_tokens = [x.strip() for x in cmp_q.replace("，", ",").split(",") if x.strip()]
            cmp_list = []
            seen_tk = set()
            with st.spinner("종목들을 찾아 점수를 매기는 중…"):
                for tok in raw_tokens[:3]:   # 최대 3개
                    tkc, _nm = search_ticker(tok)
                    if not tkc or tkc in seen_tk:
                        if not tkc:
                            cmp_list.append({"query": tok, "error": True})
                        continue
                    seen_tk.add(tkc)
                    try:
                        rr = score_stock(tkc, None)
                    except Exception:
                        rr = None
                    if rr:
                        cmp_list.append({"query": tok, "error": False, "tk": tkc, "r": rr})
                    else:
                        cmp_list.append({"query": tok, "error": True})
            st.session_state["sf_cmp_results"] = cmp_list

        cmp_results = st.session_state.get("sf_cmp_results")
        if cmp_results:
            valid = [c for c in cmp_results if not c["error"]]
            bad = [c for c in cmp_results if c["error"]]
            if bad:
                st.caption("찾지 못한 입력: " + ", ".join(c["query"] for c in bad))
            if len(valid) < 2:
                st.info("비교하려면 유효한 종목이 2개 이상 필요해요.")
            else:
                def _score_color(v):
                    try:
                        v = float(v)
                    except Exception:
                        return "#7F77DD"
                    return "#5DCAA5" if v >= 70 else ("#7F77DD" if v >= 50 else "#F0997B")

                def _bar(label, v):
                    try:
                        w = max(0, min(100, float(v)))
                        vtxt = f"{int(round(float(v)))}"
                    except Exception:
                        w, vtxt = 0, "—"
                    col = _score_color(v)
                    return (
                        "<div style='margin:7px 0'>"
                        "<div style='display:flex;justify-content:space-between;font-size:12px;color:#9BA0C4;margin-bottom:3px'>"
                        f"<span>{label}</span><span style='color:#F4F5FF;font-weight:700'>{vtxt}</span></div>"
                        "<div style='background:rgba(255,255,255,0.07);border-radius:5px;height:9px'>"
                        f"<div style='width:{w}%;height:100%;background:{col};border-radius:5px'></div></div></div>")

                # 상단: 종목별 점수 막대 게이지
                cols = st.columns(len(valid))
                for col, c in zip(cols, valid):
                    r = c["r"]; tkc = c["tk"]
                    nm = clean_name(r.get("name", tkc))
                    total = round(((r.get("profit_score") or 0) + (r.get("stability_score") or 0)) / 2)
                    with col:
                        st.markdown(
                            f"<div style='font-weight:700;color:#F4F5FF;font-size:19px'>{tkc}</div>"
                            f"<div style='color:#8a90bf;font-size:12px;margin-bottom:10px;"
                            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{nm}</div>"
                            + _bar("종합", total)
                            + _bar("수익성", r.get("profit_score", "—"))
                            + _bar("안정성", r.get("stability_score", "—")),
                            unsafe_allow_html=True)

                # 하단: 지표 비교표 (전체 폭). $ 충돌을 피하려고 현재가는 헤더에 단위 표기
                metrics = [
                    ("PER", lambda r: f"{r['per']}" if r.get("per") is not None else "—"),
                    ("현재가 ($)", lambda r: f"{r['current_price']:,}" if r.get("current_price") is not None else "—"),
                    ("상승여력", lambda r: f"{r['upside_pct']}%" if r.get("upside_pct") is not None else "—"),
                    ("변동성", lambda r: f"{r['volatility']}" if r.get("volatility") is not None else "—"),
                    ("부채비율", lambda r: f"{r['debt_to_equity']}%" if r.get("debt_to_equity") is not None else "—"),
                    ("투자의견", lambda r: r.get("analyst_rec") or "—"),
                ]
                th = ("<th style='text-align:left;padding:8px 10px;color:#9BA0C4;font-weight:500;"
                      "border-bottom:1px solid rgba(175,169,236,0.2)'>지표</th>")
                for c in valid:
                    th += (f"<th style='text-align:right;padding:8px 10px;color:#F4F5FF;"
                           f"border-bottom:1px solid rgba(175,169,236,0.2)'>{c['tk']}</th>")
                rows_html = ""
                for mlabel, fn in metrics:
                    cells = (f"<td style='padding:7px 10px;color:#9BA0C4;"
                             f"border-bottom:1px solid rgba(175,169,236,0.06)'>{mlabel}</td>")
                    for c in valid:
                        cells += (f"<td style='padding:7px 10px;text-align:right;color:#E5E2FF;"
                                  f"border-bottom:1px solid rgba(175,169,236,0.06)'>{fn(c['r'])}</td>")
                    rows_html += f"<tr>{cells}</tr>"
                st.markdown(
                    f"<table style='width:100%;border-collapse:collapse;margin-top:16px;font-size:13px'>"
                    f"<tr>{th}</tr>{rows_html}</table>",
                    unsafe_allow_html=True)
                st.caption("막대는 0~100점 기준이에요. 점수는 이 앱 기준이며 투자 추천이 아닙니다.")

    if do_search and query.strip():
        with st.spinner("종목을 찾는 중..."):
            tk, found_name = search_ticker(query)
        if not tk:
            st.warning(f"'{query}'에 해당하는 종목을 찾지 못했어요. 티커(예: AAPL)나 영어 회사명으로 다시 시도해보세요.")
        else:
            st.session_state["sf_ticker"] = tk
            st.session_state["sf_name"] = found_name
            for k in ("sf_ai", "sf_news_ai", "sf_insider", "sf_insider_ai"):
                st.session_state.pop(k, None)

    if "sf_ticker" in st.session_state:
        tk = st.session_state["sf_ticker"]
        with st.spinner(f"{tk} 분석 중..."):
            r = score_stock(tk, None)

        name = clean_name(r.get("name", tk))
        tag = "ETF" if r.get("is_etf") else "개별주"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin:8px 0 14px'>"
            f"<span style='font-size:22px;font-weight:600;color:#F4F5FF'>{name}</span>"
            f"<span style='background:rgba(175,169,236,0.15);color:#AFA9EC;font-size:13px;padding:3px 10px;border-radius:6px'>{tk}</span>"
            f"<span style='background:rgba(127,119,221,0.15);color:#C5C9E8;font-size:12px;padding:3px 10px;border-radius:6px'>{tag}</span></div>",
            unsafe_allow_html=True)

        # 점수
        total = round(((r.get("profit_score") or 0) + (r.get("stability_score") or 0)) / 2)
        m1, m2, m3 = st.columns(3)
        m1.metric("종합 점수", f"{total} / 100")
        m2.metric("수익성", f"{r.get('profit_score', '—')} / 100")
        m3.metric("안정성", f"{r.get('stability_score', '—')} / 100")

        details = []
        if r.get("per"): details.append(f"PER {r['per']}")
        if r.get("volatility"): details.append(f"변동성 {r['volatility']}")
        if r.get("debt_to_equity"): details.append(f"부채비율 {r['debt_to_equity']}%")
        if r.get("upside_pct"): details.append(f"상승여력 {r['upside_pct']}%")
        if details:
            st.caption("  ·  ".join(details))

        # 배당수익률
        if r.get("dividend_yield") is not None:
            st.markdown(
                f"<div style='color:#C5C9E8;font-size:13px;margin:8px 0'>"
                f"💰 배당수익률 <b style='color:#AFA9EC'>{r['dividend_yield']}%</b> "
                f"<span style='color:#6E7396'>· 이 주식을 1년 들고 있을 때 받는 배당이 현재 주가의 몇 %인지예요. "
                f"(0%면 배당을 거의 안 주는 회사예요.)</span></div>",
                unsafe_allow_html=True)

        # 52주 최고/최저 대비 현재 위치
        if r.get("week52_pos") is not None:
            pos = r["week52_pos"]
            st.markdown(
                f"<div style='margin:10px 0 6px'>"
                f"<div style='font-weight:500;color:#E5E2FF;margin-bottom:4px'>52주 가격 위치</div>"
                f"<div style='display:flex;justify-content:space-between;font-size:12px;color:#8a90bf;margin-bottom:3px'>"
                f"<span>최저 ${r.get('week52_low')}</span>"
                f"<span style='color:#AFA9EC'>현재 {pos}%</span>"
                f"<span>최고 ${r.get('week52_high')}</span></div>"
                f"<div style='background:rgba(255,255,255,0.06);border-radius:5px;height:10px'>"
                f"<div style='width:{pos}%;height:100%;background:linear-gradient(90deg,#5DCAA5,#EF9F27,#F0997B);border-radius:5px'></div></div>"
                f"<div style='color:#6E7396;font-size:12px;margin-top:3px'>0%면 최근 1년 중 가장 쌀 때, 100%면 가장 비쌀 때 근처예요. "
                f"(높다고 나쁜 건 아니고, '지금 1년 범위 어디쯤'인지 감 잡는 용도예요.)</div></div>",
                unsafe_allow_html=True)

        # 주가 차트 (기간/주기 선택)
        st.markdown("<div style='font-weight:500;color:#E5E2FF;margin:14px 0 4px'>주가 추이</div>", unsafe_allow_html=True)
        RANGE_OPTS = {
            "1개월 (일별)": ("1mo", "1d"),
            "6개월 (일별)": ("6mo", "1d"),
            "1년 (일별)": ("1y", "1d"),
            "5년 (주별)": ("5y", "1wk"),
            "20년 (월별)": ("20y", "1mo"),
        }
        sel = st.radio("차트 기간", list(RANGE_OPTS.keys()), index=4,
                       horizontal=True, key="sf_chart_range", label_visibility="collapsed")
        _period, _interval = RANGE_OPTS[sel]
        with st.spinner("차트 데이터 불러오는 중..."):
            dates, closes = get_price_history(tk, period=_period, interval=_interval)
        if dates:
            import pandas as pd
            df = pd.DataFrame({"종가($)": closes}, index=dates)
            st.line_chart(df, color="#7F77DD", height=280)
            chg = (closes[-1] / closes[0] - 1) * 100 if closes[0] else 0
            st.caption(f"{dates[0]} ${closes[0]:,.2f} → {dates[-1]} ${closes[-1]:,.2f}  ·  {sel} 기준 {chg:+,.0f}%")
        else:
            st.caption("이 기간의 차트 데이터를 불러오지 못했어요. 다른 기간 버튼을 눌러보세요.")

        # 애널리스트 의견
        if r.get("analyst_rec") or r.get("target_mean"):
            a_lines = []
            if r.get("analyst_rec"):
                cnt = f" ({r['analyst_count']}명)" if r.get("analyst_count") else ""
                a_lines.append(f"투자의견: {r['analyst_rec']}{cnt}")
            if r.get("target_mean"):
                tline = f"목표주가 평균: ${r['target_mean']} <span style='color:#8a90bf;font-size:12px'>(향후 12개월 기준)</span>"
                if r.get("target_low") and r.get("target_high"):
                    tline += f"<br><span style='color:#8a90bf'>최저 ${r['target_low']} ~ 최고 ${r['target_high']}</span>"
                a_lines.append(tline)
            if r.get("current_price"):
                a_lines.append(f"현재가: ${r['current_price']}")
            st.markdown(
                f"<div style='font-weight:500;color:#E5E2FF;margin:14px 0 6px'>애널리스트 의견</div>"
                f"<div style='color:#C5C9E8;font-size:14px;line-height:1.8'>{'<br>'.join(a_lines)}</div>",
                unsafe_allow_html=True)

        # AI 종합 설명
        if api_key:
            if st.button("AI 종합 설명 보기"):
                with st.spinner("AI가 설명을 작성 중..."):
                    st.session_state["sf_ai"] = explain_stock(r)
            if "sf_ai" in st.session_state:
                ai_text_box(st.session_state["sf_ai"], tone="purple")
        else:
            st.caption("AI 설명을 보려면 왼쪽 사이드바에 Gemini API 키를 넣어주세요.")

        # 최신 뉴스 (펼쳐보기 + AI 요약)
        news_items = get_news(tk, limit=10)
        if news_items:
            st.markdown("<div style='font-weight:500;color:#E5E2FF;margin:14px 0 4px'>최신 뉴스</div>", unsafe_allow_html=True)
            if api_key:
                if st.button("뉴스 핵심 요약"):
                    with st.spinner("AI가 뉴스를 요약 중..."):
                        st.session_state["sf_news_ai"] = summarize_news(name, news_items, tk)
                if "sf_news_ai" in st.session_state:
                    ai_text_box(st.session_state["sf_news_ai"], tone="purple")
            with st.expander(f"뉴스 전체 보기 ({len(news_items)}건)"):
                for n in news_items:
                    meta = " · ".join(x for x in [n.get("publisher", ""), n.get("time", "")] if x)
                    if n.get("link"):
                        st.markdown(f"- [{n['title']}]({n['link']})  \n<span style='color:#8a90bf;font-size:12px'>{meta}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"- {n['title']}  \n<span style='color:#8a90bf;font-size:12px'>{meta}</span>", unsafe_allow_html=True)

        # 내부자 거래 (개별주만)
        if not r.get("is_etf"):
            st.markdown("<div style='font-weight:500;color:#E5E2FF;margin:14px 0 4px'>내부자 거래 (임원·이사)</div>", unsafe_allow_html=True)
            if st.button("내부자 거래 보기"):
                with st.spinner("SEC에서 내부자 거래를 불러오는 중..."):
                    st.session_state["sf_insider"] = get_insider_trades(tk, limit=8)
            if "sf_insider" in st.session_state:
                trades = st.session_state["sf_insider"]
                if not trades:
                    st.caption("최근 내부자 거래 기록을 찾지 못했어요.")
                else:
                    if api_key:
                        if st.button("내부자 거래 핵심 요약"):
                            with st.spinner("AI가 요약 중..."):
                                st.session_state["sf_insider_ai"] = summarize_insider(name, trades)
                        if "sf_insider_ai" in st.session_state:
                            ai_text_box(st.session_state["sf_insider_ai"], tone="purple")
                    with st.expander(f"내부자 거래 전체 보기 ({len(trades)}건)"):
                        for t in trades:
                            head = f"**{t['name']}**" + (f" · {t['title']}" if t.get("title") else "") + f"  \n<span style='color:#8a90bf;font-size:12px'>{t['date']}</span>"
                            st.markdown(head, unsafe_allow_html=True)
                            for tx in t.get("txns", []):
                                color = {"buy": "#5DCAA5", "sell": "#E8896B"}.get(tx["kind"], "#AFA9EC")
                                detail = f"{tx['label']}"
                                if tx.get("shares"): detail += f" · {tx['shares']:,}주"
                                if tx.get("price"): detail += f" · ${tx['price']}"
                                st.markdown(f"<span style='color:{color};font-size:13px'>　{detail}</span>", unsafe_allow_html=True)

        st.caption("무료 데이터 기반이며, 정보 제공용입니다. 투자 판단의 책임은 본인에게 있습니다.")


elif page == "미국 정부·정책 분석":
    st.markdown(
        "<div style='border-bottom:1px solid rgba(175,169,236,0.2);padding-bottom:14px;margin-bottom:18px'>"
        "<div style='font-size:28px;font-weight:700;font-family:Orbitron,sans-serif;color:#F4F5FF;letter-spacing:0.5px;text-shadow:0 0 18px rgba(127,119,221,0.5)'>POLICY RADAR</div>"
        "<div style='color:#9BA0C4;font-size:14px;margin-top:4px'>현 미국 정부·대통령의 최근 정책 동향을 웹에서 찾아, 영향받을 수 있는 산업·종목을 AI가 분석합니다.</div>"
        "</div>",
        unsafe_allow_html=True)

    # 정치적 중립 + 면책 안내
    st.markdown(
        "<div style='background:rgba(240,153,123,0.08);border:0.5px solid rgba(240,153,123,0.3);"
        "border-radius:10px;padding:12px 16px;margin-bottom:14px;color:#E5D5CC;font-size:13px;line-height:1.7'>"
        "이 페이지는 <b>정치적으로 중립</b>이며 특정 정당·정치인을 지지·비판하지 않습니다. "
        "AI가 웹 검색으로 모은 정보를 정리한 <b>교육용 분석</b>일 뿐, 매수·매도 추천이 아닙니다. "
        "정책과 주가의 관계는 불확실하며, 정책은 언제든 바뀔 수 있습니다."
        "</div>",
        unsafe_allow_html=True)

    if not api_key:
        st.warning("이 기능은 AI 검색을 사용해요. 왼쪽 사이드바에 Gemini API 키를 먼저 넣어주세요.")
    else:
        tab_pol, tab_tl, tab_rmk = st.tabs(["📈 정책 동향", "🏛️ 분야별 4년 흐름", "🗣️ 대통령 발언"])

        # ── 탭 1: 정책 동향 (관심 분야 입력) ─────────────────
        with tab_pol:
            st.caption("관심 분야를 고르거나 직접 적으면, 최근 미국 정부 정책 동향과 영향받을 산업·종목을 정리해드려요. (비워두면 전반적 동향)")

            # 빠른 선택 칩
            POLICY_TOPICS = ["전반적 동향", "반도체", "관세·무역", "금리·세금",
                             "에너지", "방산·국방", "AI 규제", "헬스케어"]
            pt_cols = st.columns(4)
            topic_click = None
            for i, t in enumerate(POLICY_TOPICS):
                if pt_cols[i % 4].button(t, key=f"policy_topic_{i}", use_container_width=True):
                    topic_click = "" if t == "전반적 동향" else t

            c1, c2 = st.columns([4, 1])
            with c1:
                focus = st.text_input(
                    "관심 분야",
                    placeholder="또는 직접 입력 (예: 이민, 우주·항공, 노동시장 …)",
                    label_visibility="collapsed", key="policy_focus_input")
            with c2:
                do_policy = st.button("분석하기", type="primary", use_container_width=True, key="policy_do")
            st.caption("AI가 직접 웹을 검색하므로 10~30초쯤 걸릴 수 있어요. 결과는 매번 조금씩 달라집니다.")

            run_focus = topic_click if topic_click is not None else (focus if do_policy else None)
            if run_focus is not None:
                with st.spinner("최근 미국 정부 정책을 웹에서 찾아 분석하는 중…"):
                    data, err = analyze_government_policy(run_focus)
                if err:
                    st.session_state["policy_err"] = err
                    st.session_state.pop("policy_data", None)
                else:
                    st.session_state["policy_data"] = data
                    st.session_state["policy_focus"] = run_focus.strip()
                    st.session_state.pop("policy_err", None)
                    st.session_state.pop("policy_search_pick", None)

            if st.session_state.get("policy_err"):
                st.error(st.session_state["policy_err"])

            data = st.session_state.get("policy_data")
            if data:
                shown_focus = st.session_state.get("policy_focus")
                if shown_focus:
                    st.markdown(
                        f"<div style='color:#9BA0C4;font-size:13px;margin:4px 0 2px'>관심 분야: "
                        f"<span style='color:#AFA9EC'>{shown_focus}</span></div>",
                        unsafe_allow_html=True)
                st.subheader("최근 정책 동향과 영향 분석")
                ai_text_box(data.get("text", ""), tone="purple")
                policy_sources_expander(data)
                policy_ticker_section(data.get("tickers") or [], key_prefix="policy_search",
                                      names=data.get("ticker_names") or {})

        # ── 탭 2: 분야별 최근 4년 흐름 ───────────────────────
        with tab_tl:
            st.caption("분야를 누르면, 미국 정부가 그 분야에서 최근 4년간 무슨 정책·발언을 했고 어떤 영향을 줬는지 타임라인으로 정리해드려요.")
            SECTORS = ["반도체", "AI 인프라", "에너지", "방산·국방",
                       "제약·바이오", "관세·무역", "암호화폐", "전기차·배터리"]
            sec_cols = st.columns(4)
            for i, sec in enumerate(SECTORS):
                if sec_cols[i % 4].button(sec, key=f"policy_sec_{i}", use_container_width=True):
                    with st.spinner(f"'{sec}' 분야의 최근 4년 정책 흐름을 웹에서 찾는 중…"):
                        tdata, terr = analyze_sector_policy_timeline(sec)
                    if terr:
                        st.session_state["policy_timeline_err"] = terr
                        st.session_state.pop("policy_timeline_data", None)
                    else:
                        st.session_state["policy_timeline_data"] = tdata
                        st.session_state["policy_timeline_sector"] = sec
                        st.session_state.pop("policy_timeline_err", None)
                        st.session_state.pop("policy_tl_pick", None)

            if st.session_state.get("policy_timeline_err"):
                st.error(st.session_state["policy_timeline_err"])

            tdata = st.session_state.get("policy_timeline_data")
            if tdata:
                sec_name = st.session_state.get("policy_timeline_sector", "")
                st.markdown(
                    f"<div style='font-size:20px;font-weight:700;color:#F4F5FF;margin:14px 0 4px'>"
                    f"🏛️ {sec_name} · 최근 4년 정책 타임라인</div>",
                    unsafe_allow_html=True)
                ai_text_box(tdata.get("text", ""), tone="purple")
                policy_sources_expander(tdata)
                policy_ticker_section(tdata.get("tickers") or [], key_prefix="policy_tl",
                                      names=tdata.get("ticker_names") or {})

        # ── 탭 3: 대통령 발언 모아보기 ───────────────────────
        with tab_rmk:
            st.caption("현 미국 대통령이 최근 공개적으로 한 발언을 출처와 함께 모아드려요. "
                       "'정책 흐름'이 아니라 '대통령이 직접 한 말' 중심이에요. "
                       "(가짜·왜곡 인용이 많은 주제라, 출처로 확인된 발언만 담았어요. 출처를 꼭 함께 확인하세요.)")

            if st.button("📋 전체 발언 분야별로 모아보기", key="remarks_overview_btn",
                         type="primary", use_container_width=True):
                with st.spinner("대통령의 최근 발언을 웹에서 찾아 분야별로 정리하는 중…"):
                    ov, ov_err = analyze_remarks_overview()
                if ov_err:
                    st.session_state["remarks_ov_err"] = ov_err
                    st.session_state.pop("remarks_ov_data", None)
                else:
                    st.session_state["remarks_ov_data"] = ov
                    st.session_state.pop("remarks_ov_err", None)
                    st.session_state.pop("remarks_ov_pick", None)

            if st.session_state.get("remarks_ov_err"):
                st.error(st.session_state["remarks_ov_err"])

            ov = st.session_state.get("remarks_ov_data")
            if ov:
                st.markdown(
                    "<div style='font-size:20px;font-weight:700;color:#F4F5FF;margin:14px 0 4px'>"
                    "🗣️ 분야별 발언 요약</div>", unsafe_allow_html=True)
                ai_text_box(ov.get("text", ""), tone="purple")
                policy_sources_expander(ov)
                policy_ticker_section(ov.get("tickers") or [], key_prefix="remarks_ov",
                                      names=ov.get("ticker_names") or {})

            st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
            st.caption("특정 분야만 자세히 — 아래 분야를 누르면 그 분야 발언만 시기순으로 모아드려요.")
            REMARK_SECTORS = ["반도체", "AI 인프라", "에너지", "방산·국방",
                              "제약·바이오", "관세·무역", "암호화폐", "전기차·배터리"]
            rs_cols = st.columns(4)
            for i, sec in enumerate(REMARK_SECTORS):
                if rs_cols[i % 4].button(sec, key=f"remarks_sec_{i}", use_container_width=True):
                    with st.spinner(f"'{sec}' 분야 발언을 웹에서 찾는 중…"):
                        rdata, rerr = analyze_remarks_sector(sec)
                    if rerr:
                        st.session_state["remarks_sec_err"] = rerr
                        st.session_state.pop("remarks_sec_data", None)
                    else:
                        st.session_state["remarks_sec_data"] = rdata
                        st.session_state["remarks_sec_name"] = sec
                        st.session_state.pop("remarks_sec_err", None)
                        st.session_state.pop("remarks_sec_pick", None)

            if st.session_state.get("remarks_sec_err"):
                st.error(st.session_state["remarks_sec_err"])

            rdata = st.session_state.get("remarks_sec_data")
            if rdata:
                rsec = st.session_state.get("remarks_sec_name", "")
                st.markdown(
                    f"<div style='font-size:20px;font-weight:700;color:#F4F5FF;margin:14px 0 4px'>"
                    f"🗣️ {rsec} · 대통령 발언 모음</div>", unsafe_allow_html=True)
                ai_text_box(rdata.get("text", ""), tone="purple")
                policy_sources_expander(rdata)
                policy_ticker_section(rdata.get("tickers") or [], key_prefix="remarks_sec",
                                      names=rdata.get("ticker_names") or {})

        st.caption("AI·웹검색 기반 교육용 분석이며, 투자 판단의 책임은 본인에게 있습니다.")


elif page == "관심 많은 분야":
    st.markdown(
        "<div style='border-bottom:1px solid rgba(175,169,236,0.2);padding-bottom:14px;margin-bottom:18px'>"
        "<div style='font-size:28px;font-weight:700;font-family:Orbitron,sans-serif;color:#F4F5FF;letter-spacing:0.5px;text-shadow:0 0 18px rgba(127,119,221,0.5)'>HOT THEMES</div>"
        "<div style='color:#9BA0C4;font-size:14px;margin-top:4px'>요즘 미국 증시에서 관심·화제가 쏠리는 분야를 순위로 보여드려요. 각 분야에서 많이 거론되는 종목도 함께요.</div>"
        "</div>", unsafe_allow_html=True)

    st.markdown(
        "<div style='background:rgba(240,153,123,0.08);border:0.5px solid rgba(240,153,123,0.3);"
        "border-radius:10px;padding:12px 16px;margin-bottom:14px;color:#E5D5CC;font-size:13px;line-height:1.7'>"
        "여기는 <b>'요즘 화제가 되는 분야'</b>를 정리한 것이지 <b>추천이 아니에요.</b> "
        "특히 ⚠️ <b>관심이 많다 = 좋은 투자가 아니에요.</b> 화제가 몰린 분야는 이미 가격이 많이 올라 "
        "<b>고평가·과열</b>일 수도 있어요. 인기는 '지금 무슨 얘기가 도는지' 참고용으로만 보세요."
        "</div>", unsafe_allow_html=True)

    if not api_key:
        st.warning("이 기능은 AI 검색을 사용해요. 왼쪽 사이드바에 Gemini API 키를 먼저 넣어주세요.")
    else:
        sub_hot, sub_mine = st.tabs(["🔥 요즘 뜨는 분야", "🎯 내 관심 분야 고르기"])

        # ── 서브탭 1: AI가 골라주는 요즘 뜨는 분야 ──
        with sub_hot:
            if st.button("🔥 요즘 관심 많은 분야 순위 보기", type="primary",
                         use_container_width=True, key="trend_btn"):
                with st.spinner("요즘 화제가 되는 분야를 웹에서 찾는 중… (10~30초)"):
                    trdata, trerr = analyze_trending_sectors()
                if trerr:
                    st.session_state["trend_err"] = trerr
                    st.session_state.pop("trend_data", None)
                else:
                    st.session_state["trend_data"] = trdata
                    st.session_state.pop("trend_err", None)
                    st.session_state.pop("trend_pick", None)
            st.caption("AI가 직접 웹을 검색하므로 시간이 좀 걸려요. 결과는 매번 조금씩 달라집니다.")
            if st.session_state.get("trend_err"):
                st.error(st.session_state["trend_err"])
            trdata = st.session_state.get("trend_data")
            if trdata:
                st.subheader("요즘 관심이 쏠리는 분야")
                ai_text_box(trdata.get("text", ""), tone="purple")
                policy_sources_expander(trdata)
                policy_ticker_section(trdata.get("tickers") or [], key_prefix="trend",
                                      names=trdata.get("ticker_names") or {})

        # ── 서브탭 2: 내가 직접 고른 분야 ──
        with sub_mine:
            st.caption("궁금한 분야를 눌러보세요. 그 분야에서 요즘 거론되는 종목과 이유를 정리해드려요.")
            MY_SECTORS = ["반도체", "AI 인프라", "에너지", "방산·국방",
                          "제약·바이오", "관세·무역", "암호화폐", "전기차·배터리",
                          "원자력", "로봇·자동화", "우주·항공", "금융·은행"]
            ms_cols = st.columns(4)
            clicked = None
            for i, sec in enumerate(MY_SECTORS):
                if ms_cols[i % 4].button(sec, key=f"myfocus_sec_{i}", use_container_width=True):
                    clicked = sec
            typed = st.text_input("또는 직접 입력", key="myfocus_text",
                                  label_visibility="collapsed",
                                  placeholder="또는 직접 입력 (예: 비만치료제, 데이터센터 …)")
            if st.button("입력한 분야 살펴보기", key="myfocus_btn") and typed.strip():
                clicked = typed.strip()
            if clicked:
                st.session_state["myfocus_q"] = clicked
                with st.spinner(f"'{clicked}' 분야를 웹에서 살펴보는 중… (10~30초)"):
                    fdata, ferr = analyze_sector_focus(clicked)
                if ferr:
                    st.session_state["myfocus_err"] = ferr
                    st.session_state.pop("myfocus_data", None)
                else:
                    st.session_state["myfocus_data"] = fdata
                    st.session_state.pop("myfocus_err", None)
                    st.session_state.pop("myfocus_pick", None)
            if st.session_state.get("myfocus_err"):
                st.error(st.session_state["myfocus_err"])
            fdata = st.session_state.get("myfocus_data")
            if fdata:
                st.subheader(f"🎯 {st.session_state.get('myfocus_q','')} · 요즘 거론되는 종목")
                ai_text_box(fdata.get("text", ""), tone="purple")
                policy_sources_expander(fdata)
                policy_ticker_section(fdata.get("tickers") or [], key_prefix="myfocus",
                                      names=fdata.get("ticker_names") or {})

        st.caption("AI·웹검색 기반 교육용 정리이며, 투자 판단의 책임은 본인에게 있습니다.")


st.divider()
st.caption("※ 정보 제공용이며 투자 판단의 책임은 본인에게 있습니다.")
