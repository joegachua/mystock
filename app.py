import streamlit as st
from score_engine import score_stock as _score_stock
from ai_explain import init_client, explain_stock, summarize_news, extract_holdings_from_images, summarize_insider
from news_fetch import get_news as _get_news
from insider_fetch import get_insider_trades as _get_insider_trades
from superinvestor_fetch import get_13f_holdings as _get_13f_holdings, SUPER_INVESTORS, guess_ticker as _guess_ticker
from stock_search import search_ticker as _search_ticker, get_price_history as _get_price_history

# ── 캐싱 래퍼 ──────────────────────────────────────────────
# 같은 종목/데이터를 반복 조회할 때 메모리에 잠시 저장해 속도·서버 부담을 줄인다.
@st.cache_data(ttl=600, show_spinner=False)   # 점수: 10분
def score_stock(ticker, user_return_pct=None):
    return _score_stock(ticker, user_return_pct)

@st.cache_data(ttl=600, show_spinner=False)   # 뉴스: 10분
def get_news(ticker, limit=4):
    return _get_news(ticker, limit)

@st.cache_data(ttl=1800, show_spinner=False)  # 내부자 거래: 30분
def get_insider_trades(ticker, limit=8):
    return _get_insider_trades(ticker, limit)

@st.cache_data(ttl=3600, show_spinner=False)  # 13F: 1시간 (분기마다 바뀌므로 길게)
def get_13f_holdings(cik, top_n=None):
    return _get_13f_holdings(cik, top_n)

@st.cache_data(ttl=86400, show_spinner=False) # 회사명→티커 매칭: 하루
def guess_ticker(company_name):
    return _guess_ticker(company_name)

@st.cache_data(ttl=3600, show_spinner=False)  # 검색: 1시간
def search_ticker(query):
    return _search_ticker(query)

@st.cache_data(ttl=3600, show_spinner=False)  # 주가 차트: 1시간
def get_price_history(ticker, period="20y"):
    return _get_price_history(ticker, period)
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

# ===== 사이드바: 메뉴 + Gemini API 키 =====
with st.sidebar:
    st.markdown("### 메뉴")
    page = st.radio("페이지 선택", ["내 포트폴리오 분석", "부자들은 요즘 뭘 샀나", "종목 검색"],
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

    with st.expander("포트폴리오 캡처로 자동 입력 (토스 등)"):
        st.caption("캡처에 종목명과 수익률이 보이게 찍어주세요. 여러 장도 가능합니다.")
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
                    data, err = extract_holdings_from_images(imgs)
                if err:
                    st.error(err)
                elif data:
                    rows = []
                    for d in data:
                        rows.append({"티커": d.get("ticker", ""), "수익률(%)": d.get("return_pct")})
                    st.session_state["holdings_df"] = rows
                    st.success(f"{len(data)}개 종목을 인식했어요. 아래 표에 채웠으니 확인 후 수정하세요.")
                    st.rerun()

    import pandas as pd
    default_rows = st.session_state.get("holdings_df", [
        {"티커": "NVDA", "수익률(%)": 17.3},
        {"티커": "TEVA", "수익률(%)": 102.5},
        {"티커": "NVO", "수익률(%)": -24.5},
        {"티커": "GOOGL", "수익률(%)": 30.9},
        {"티커": "SPY", "수익률(%)": 22.2},
        {"티커": "CPNG", "수익률(%)": -6.1},
    ])
    edited = st.data_editor(
        pd.DataFrame(default_rows),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "티커": st.column_config.TextColumn("티커", help="예: NVDA", width="medium"),
            "수익률(%)": st.column_config.NumberColumn("수익률 (%)", help="토스에서 보이는 총 수익률", format="%.1f"),
        },
        key="holdings_editor",
    )

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
                results.append(r)
            except Exception as e:
                results.append({"ticker": ticker, "name": ticker, "error": str(e)})
            progress.progress((i + 1) / len(valid), text=f"{ticker} 분석 완료")
        progress.empty()
        st.session_state["results"] = results
        st.session_state["my_tickers"] = [r["ticker"] for r in results if "error" not in r]

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
            st.divider()

        st.subheader("종목별 점수 (높은 순)")
        for idx, r in enumerate(ok):
            tag = "ETF" if r.get("is_etf") else "개별주"
            total = round(total_score(r))
            name = clean_name(r["name"])
            with st.expander(f"{name}  ·  {tag}  ·  종합 {total}점"):
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

                exp_key = f"explain_{r['ticker']}_{idx}"
                if st.button("AI 설명 보기", key=f"btn_{exp_key}"):
                    if not api_key:
                        st.warning("왼쪽 사이드바에 Gemini API 키를 먼저 넣어주세요.")
                    else:
                        with st.spinner("AI가 설명을 작성 중..."):
                            st.session_state[exp_key] = explain_stock(r)
                if exp_key in st.session_state:
                    safe_text = st.session_state[exp_key].replace("#", "").replace("**", "")
                    safe_text = safe_text.replace("\n", "<br>")
                    st.markdown(
                        f"<div style='background:rgba(127,119,221,0.12);border:0.5px solid rgba(175,169,236,0.3);border-radius:10px;padding:14px 16px;color:#E5E2FF;font-size:14px;line-height:1.8'>{safe_text}</div>",
                        unsafe_allow_html=True)

                st.markdown("**최신 뉴스**")
                news_items = get_news(r["ticker"], limit=10)
                if news_items:
                    sum_key = f"newsum_{r['ticker']}_{idx}"
                    if st.button("뉴스 핵심 요약", key=f"sumbtn_{sum_key}"):
                        if not api_key:
                            st.warning("왼쪽 사이드바에 Gemini API 키를 먼저 넣어주세요.")
                        else:
                            with st.spinner("AI가 뉴스를 요약 중..."):
                                st.session_state[sum_key] = summarize_news(clean_name(r["name"]), news_items)
                    if sum_key in st.session_state:
                        st.success(st.session_state[sum_key])

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
                    st.markdown("<div style='font-weight:500;color:#E5E2FF;margin-top:10px'>내부자 거래 (임원·이사)</div>", unsafe_allow_html=True)
                    if st.button("내부자 거래 보기", key=f"insbtn_{ins_key}"):
                        with st.spinner("SEC에서 내부자 거래를 불러오는 중..."):
                            st.session_state[ins_key] = get_insider_trades(r["ticker"], limit=8)
                    if ins_key in st.session_state:
                        trades = st.session_state[ins_key]
                        if not trades:
                            st.caption("최근 내부자 거래 기록이 없어요.")
                        else:
                            insum_key = f"inssum_{r['ticker']}_{idx}"
                            if st.button("내부자 거래 핵심 요약", key=f"inssumbtn_{insum_key}"):
                                if not api_key:
                                    st.warning("왼쪽 사이드바에 Gemini API 키를 먼저 넣어주세요.")
                                else:
                                    with st.spinner("AI가 내부자 거래를 요약 중..."):
                                        st.session_state[insum_key] = summarize_insider(clean_name(r["name"]), trades)
                            if insum_key in st.session_state:
                                st.success(st.session_state[insum_key])

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

    inv_name = st.selectbox("투자자 / 기관 선택", list(SUPER_INVESTORS.keys()))
    if st.button("보유 종목 보기", type="primary"):
        cik = SUPER_INVESTORS[inv_name]
        with st.spinner(f"SEC에서 {inv_name}의 13F를 불러오는 중..."):
            report_date, holdings = get_13f_holdings(cik)
        st.session_state["si_result"] = (inv_name, report_date, holdings)
        for k in ("si_ai", "si_small_ai", "si_show_all", "si_page", "si_open_stock", "si_stock_ai"):
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

            # 시총 조회 (작은 회사 집중 매수 판단)
            import yfinance as yf
            from superinvestor_fetch import classify_size
            my_tickers = set(st.session_state.get("my_tickers", []))
            overlaps = []
            small_bets = []
            with st.spinner("종목별 시가총액 확인 중..."):
                for h in holdings:
                    h["_ticker"] = guess_ticker(h["name"])
                    h["_weight"] = h["value"] / total_val * 100
                    h["_mcap"] = None
                    if h["_ticker"]:
                        try:
                            h["_mcap"] = yf.Ticker(h["_ticker"]).info.get("marketCap")
                        except Exception:
                            pass
                    if h["_mcap"] and h["_mcap"] < 10e9 and h["_weight"] >= 5:
                        small_bets.append(h)

            # 내 종목 겹침
            if my_tickers:
                for h in holdings:
                    if h["_ticker"] and h["_ticker"] in my_tickers:
                        overlaps.append((h["name"], h["_ticker"]))
                if overlaps:
                    ov = ", ".join(f"{n} ({t})" for n, t in overlaps)
                    st.markdown(
                        f"<div style='background:rgba(159,225,203,0.10);border-left:3px solid #5DCAA5;border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:12px;color:#E5E2FF;font-size:14px'>"
                        f"<span style='color:#9FE1CB;font-weight:500'>나와 겹치는 종목</span> &nbsp;{ov}</div>",
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
                        txt = st.session_state["si_small_ai"].replace("#", "").replace("**", "").replace("\n", "<br>")
                        st.markdown(
                            f"<div style='background:rgba(240,153,123,0.08);border:0.5px solid rgba(240,153,123,0.25);border-radius:10px;padding:14px 16px;margin-bottom:10px;color:#E5E2FF;font-size:14px;line-height:1.8'>{txt}</div>",
                            unsafe_allow_html=True)

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
                    txt = st.session_state["si_ai"].replace("#", "").replace("**", "").replace("\n", "<br>")
                    st.markdown(
                        f"<div style='background:rgba(127,119,221,0.10);border:0.5px solid rgba(175,169,236,0.25);border-radius:10px;padding:14px 16px;margin-bottom:10px;color:#E5E2FF;font-size:14px;line-height:1.8'>{txt}</div>",
                        unsafe_allow_html=True)

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
                    tags += f" · {size}"
                label = f"{i}. {h['name']}{tags}    ${h['value']/1e6:,.0f}M ({h['_weight']:.1f}%)"
                if st.button(label, key=f"stk_{start}_{i}", use_container_width=True):
                    cur = st.session_state.get("si_open_stock")
                    st.session_state["si_open_stock"] = None if cur == h["name"] else h["name"]
                    st.session_state.pop("si_stock_ai", None)
                    st.rerun()

                # 종목 상세 펼침
                if st.session_state.get("si_open_stock") == h["name"]:
                    tk = h["_ticker"]
                    with st.container():
                        if not tk:
                            st.caption("이 종목은 티커 매칭에 실패해서 상세 정보를 불러올 수 없어요.")
                        else:
                            # 데이터 분석 (점수)
                            try:
                                sd = score_stock(tk, None)
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
                            except Exception:
                                st.caption("데이터를 불러오지 못했어요.")

                            # 뉴스 (펼쳐보기)
                            news_items = get_news(tk, limit=8)
                            if news_items:
                                with st.expander(f"최신 뉴스 ({len(news_items)}건)"):
                                    for n in news_items:
                                        meta = " · ".join(x for x in [n.get("publisher", ""), n.get("time", "")] if x)
                                        if n.get("link"):
                                            st.markdown(f"- [{n['title']}]({n['link']})  \n<span style='color:#8a90bf;font-size:12px'>{meta}</span>", unsafe_allow_html=True)
                                        else:
                                            st.markdown(f"- {n['title']}  \n<span style='color:#8a90bf;font-size:12px'>{meta}</span>", unsafe_allow_html=True)

                            # AI 매수 이유
                            if api_key:
                                if st.button("이 종목을 왜 샀는지 AI 분석", key=f"why_{start}_{i}"):
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
                                            st.session_state["si_stock_ai"] = resp.text.strip()
                                        except Exception as e:
                                            st.session_state["si_stock_ai"] = _friendly_error(e)
                                if "si_stock_ai" in st.session_state:
                                    txt = st.session_state["si_stock_ai"].replace("#", "").replace("**", "").replace("\n", "<br>")
                                    st.markdown(
                                        f"<div style='background:rgba(127,119,221,0.10);border:0.5px solid rgba(175,169,236,0.25);border-radius:10px;padding:12px 14px;margin:6px 0;color:#E5E2FF;font-size:14px;line-height:1.8'>{txt}</div>",
                                        unsafe_allow_html=True)

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

        # 20년 주가 차트
        st.markdown("<div style='font-weight:500;color:#E5E2FF;margin:14px 0 4px'>주가 추이 (최근 20년 · 월별)</div>", unsafe_allow_html=True)
        with st.spinner("차트 데이터 불러오는 중..."):
            dates, closes = get_price_history(tk, period="20y")
        if dates:
            import pandas as pd
            df = pd.DataFrame({"종가($)": closes}, index=dates)
            st.line_chart(df, color="#7F77DD", height=280)
            chg = (closes[-1] / closes[0] - 1) * 100 if closes[0] else 0
            yrs = len(dates) / 12
            st.caption(f"{dates[0]} ${closes[0]:,.2f} → {dates[-1]} ${closes[-1]:,.2f}  ·  약 {yrs:.0f}년간 {chg:+,.0f}%")
        else:
            st.caption("차트 데이터를 불러오지 못했어요.")

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
                txt = st.session_state["sf_ai"].replace("#", "").replace("**", "").replace("\n", "<br>")
                st.markdown(
                    f"<div style='background:rgba(127,119,221,0.10);border:0.5px solid rgba(175,169,236,0.25);border-radius:10px;padding:14px 16px;margin:6px 0;color:#E5E2FF;font-size:14px;line-height:1.8'>{txt}</div>",
                    unsafe_allow_html=True)
        else:
            st.caption("AI 설명을 보려면 왼쪽 사이드바에 Gemini API 키를 넣어주세요.")

        # 최신 뉴스 (펼쳐보기 + AI 요약)
        news_items = get_news(tk, limit=10)
        if news_items:
            st.markdown("<div style='font-weight:500;color:#E5E2FF;margin:14px 0 4px'>최신 뉴스</div>", unsafe_allow_html=True)
            if api_key:
                if st.button("뉴스 핵심 요약"):
                    with st.spinner("AI가 뉴스를 요약 중..."):
                        st.session_state["sf_news_ai"] = summarize_news(name, news_items)
                if "sf_news_ai" in st.session_state:
                    txt = st.session_state["sf_news_ai"].replace("#", "").replace("**", "").replace("\n", "<br>")
                    st.markdown(
                        f"<div style='background:rgba(127,119,221,0.08);border:0.5px solid rgba(175,169,236,0.22);border-radius:10px;padding:12px 14px;margin:6px 0;color:#E5E2FF;font-size:14px;line-height:1.8'>{txt}</div>",
                        unsafe_allow_html=True)
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
                            txt = st.session_state["sf_insider_ai"].replace("#", "").replace("**", "").replace("\n", "<br>")
                            st.markdown(
                                f"<div style='background:rgba(127,119,221,0.08);border:0.5px solid rgba(175,169,236,0.22);border-radius:10px;padding:12px 14px;margin:6px 0;color:#E5E2FF;font-size:14px;line-height:1.8'>{txt}</div>",
                                unsafe_allow_html=True)
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


st.divider()
st.caption("※ 정보 제공용이며 투자 판단의 책임은 본인에게 있습니다.")