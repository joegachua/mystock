"""Gemini로 종목 점수를 쉽게 설명해주는 모듈."""
from google import genai

_client = None

def init_client(api_key):
    """API 키로 Gemini 클라이언트를 준비한다."""
    global _client
    _client = genai.Client(api_key=api_key)


def _friendly_error(e):
    """API 오류를 사용자 친화적 메시지로 변환."""
    s = str(e)
    if "429" in s or "RESOURCE_EXHAUSTED" in s or "quota" in s.lower():
        return "⏳ AI 사용량이 잠시 초과됐어요. 무료 한도 때문이니 1분쯤 후 다시 시도해주세요."
    if "API_KEY" in s or "api key" in s.lower() or "401" in s or "403" in s:
        return "🔑 API 키에 문제가 있어요. 키를 다시 확인해주세요."
    return "AI 응답을 가져오지 못했어요. 잠시 후 다시 시도해주세요."


def _simple_generate(prompt, models=("gemini-2.5-flash-lite", "gemini-2.5-flash")):
    """검색 없이 텍스트를 생성한다. 일시적 오류(429/503/과부하) 시 재시도하고,
    그래도 안 되면 다른 모델로 폴백한다. 빈 응답도 안전하게 처리.
    반환: 생성된 문자열(또는 사용자 친화적 오류 메시지)."""
    if _client is None:
        return "(API 키가 설정되지 않았어요)"
    import time
    last_err = None
    for model_name in models:
        for attempt in range(2):           # 모델당 최대 2번 시도
            try:
                resp = _client.models.generate_content(model=model_name, contents=prompt)
                text = (getattr(resp, "text", None) or "").strip()
                if text:
                    return text
                last_err = None            # 빈 응답 → 재시도/다음 모델
            except Exception as e:
                last_err = e
                es = str(e)
                transient = (any(k in es for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"))
                             or "overloaded" in es.lower())
                if not transient:
                    break                  # 일시적 오류가 아니면 같은 모델 재시도 무의미 → 다음 모델
            time.sleep(0.8 * (attempt + 1))
    if isinstance(last_err, Exception):
        return _friendly_error(last_err)
    return "AI가 빈 응답을 줬어요. 잠시 후 다시 시도해주세요. (다른 종목은 잘 될 수 있어요)"

def explain_stock(result):
    """점수 계산 결과(dict)를 받아 초보자용 한 줄 설명을 생성한다."""
    if _client is None:
        return "(API 키가 설정되지 않았어요)"

    name = result.get("name", result.get("ticker"))
    tag = "ETF" if result.get("is_etf") else "개별주"
    profit = result.get("profit_score")
    stability = result.get("stability_score")

    facts = [f"종목: {name} ({tag})",
             f"수익성 점수: {profit}/100",
             f"안정성 점수: {stability}/100"]
    if "per" in result:
        facts.append(f"PER: {result['per']}")
    if "volatility" in result:
        facts.append(f"변동성(연율화): {result['volatility']}")
    if "debt_to_equity" in result:
        facts.append(f"부채비율: {result['debt_to_equity']}")
    if "upside_pct" in result:
        facts.append(f"애널리스트 목표가 상승여력: {result['upside_pct']}%")
    if "analyst_rec" in result:
        facts.append(f"애널리스트 투자의견: {result['analyst_rec']}")
    if "analyst_count" in result:
        facts.append(f"애널리스트 수: {result['analyst_count']}명")
    if "target_mean" in result:
        facts.append(f"목표주가 평균: ${result['target_mean']}")
    if "target_high" in result:
        facts.append(f"목표주가 최고: ${result['target_high']}")
    if "target_low" in result:
        facts.append(f"목표주가 최저: ${result['target_low']}")
    if "current_price" in result:
        facts.append(f"현재가: ${result['current_price']}")

    prompt = (
        "너는 친절하고 꼼꼼한 투자 교육 도우미야. 아래 지표를 바탕으로 이 종목을 "
        "주식 초보자도 이해할 수 있게 설명해줘. 세 개의 자연스러운 문단으로 작성해:\n"
        "- 첫 문단: 이 회사가 어떤 회사이고 지금 상태가 어떤지\n"
        "- 둘째 문단: 수익성과 안정성 점수가 각각 왜 이렇게 나왔는지, 어떤 지표 때문인지 구체적으로\n"
        "- 셋째 문단: 애널리스트(증권사 전문가)들이 어떻게 보는지, 목표주가는 어느 수준인지\n\n"
        "중요: 제목이나 번호(1), 2), ## 등)를 절대 쓰지 말고 문단만 써. "
        "별표(*)나 마크다운 기호도 쓰지 마. "
        "전문용어(PER, 변동성, 부채비율 등)는 반드시 쉬운 말로 풀어서 설명하고, "
        "매수/매도 추천은 절대 하지 마. 한국어 존댓말로, 친근하지만 정확하게.\n\n"
        + "\n".join(facts)
    )

    return _simple_generate(prompt)


def summarize_news(name, news_items, ticker=None):
    """뉴스 제목 목록을 받아 한국어로 핵심을 요약한다. 종목과 무관한 뉴스는 걸러낸다."""
    if _client is None:
        return "(API 키가 설정되지 않았어요)"
    if not news_items:
        return "요약할 뉴스가 없어요."

    # 제목 + (있으면) 본문 요약을 함께 제공해 AI가 '무슨 일이 왜 일어났는지'를 파악하게 한다
    blocks = []
    for n in news_items:
        line = f"- {n['title']} ({n.get('publisher','')})"
        summ = (n.get("summary") or "").strip()
        if summ:
            line += f"\n  요약: {summ}"
        blocks.append(line)
    titles = "\n".join(blocks)
    tk_part = f"(티커: {ticker}) " if ticker else ""
    prompt = (
        f"아래는 '{name}' {tk_part}종목의 최근 영어 뉴스(제목과, 있으면 본문 요약)야. "
        "이 목록에는 해당 종목과 직접 관련 없는 일반 시장 기사가 섞여 있을 수 있어.\n\n"
        f"먼저 '{name}'와 직접 관련된 뉴스만 머릿속으로 골라낸 다음, 그걸 바탕으로 한국어로 "
        "구체적으로 설명해줘. 막연한 일반론('AI 시장이 강하다' 수준)은 금지고, 반드시 "
        "'무슨 일이 있었는지'와 '그래서 주가가 왜 오를/내릴 수 있는지'를 인과관계로 연결해서 써:\n"
        "(1) 최근 이 종목에 실제로 무슨 일/이슈가 있었는지 — 구체적인 사건·실적·계약·규제·인물 발언 등 "
        "본문 요약에 나온 사실을 근거로 (날짜나 수치가 있으면 함께)\n"
        "(2) 그 일이 '왜' 주가에 호재 또는 악재로 작용하는지 — 돈을 더 벌게 되어서/비용이 늘어서/"
        "경쟁이 심해져서 등 이유를 분명히. 호재 요인과 악재 요인을 균형 있게, '~할 수 있다'로.\n\n"
        "규칙:\n"
        "- 뉴스 제목을 그대로 나열·인용하지 마. 어떤 기사를 봤는지 적지 말고, 내용을 네 말로 풀어서.\n"
        "- 4~6문장으로 충실하게. 단, 본문 요약에 없는 사실을 지어내진 마.\n"
        "- 매수/매도 추천은 하지 마.\n"
        f"- 만약 '{name}'와 직접 관련된 구체적 뉴스가 거의 없으면, 추측해서 지어내지 말고 "
        "'최근 이 종목과 직접 관련된 구체적인 뉴스는 많지 않네요.'라고만 답해.\n\n"
        + titles
    )
    return _simple_generate(prompt)


def _recognize_one(parts_imgs):
    """이미지 묶음 하나를 인식해 [{name, return_pct}, ...] 반환. (raw_list, error)"""
    from google.genai import types
    import json, time as _time

    parts = list(parts_imgs)
    parts.append(types.Part.from_text(text=(
        "이 이미지는 한국 증권 앱(토스)의 해외주식 보유 목록 캡처야. "
        "화면에 실제로 보이는 종목을 위에서 아래 순서대로 하나도 빠짐없이 읽어줘.\n\n"
        "두 가지 원칙을 동시에 지켜:\n"
        "(A) 빠뜨리지 마: 종목 이름이 조금이라도 보이면 모두 포함. 위/아래 끝에 살짝 잘려 보이는 것도 포함.\n"
        "(B) 지어내지 마: 화면에 없는 종목을 추측으로 추가하지 마. 보이는 것만.\n\n"
        "각 종목마다:\n"
        "(1) name: 화면에 적힌 이름 그대로 (한글이면 한글로, 예: '노보노디스크', '테바', 'SPY')\n"
        "(2) ticker: 화면에 티커가 실제로 보이면 그것을 적어. 화면에 티커가 안 보이면, 그 종목명이 확실히 아는 유명 종목일 때만 티커를 적고, 조금이라도 불확실하면 null. "
        "가장 중요: 티커를 적고 싶어서 화면에 없는 종목을 추가하면 절대 안 돼. 화면에 보이는 종목 이름이 항상 우선이야.\n"
        "(3) return_pct: '총 수익' 칸의 퍼센트. 빨강이면 +, 파랑이면 -. 못 읽으면 null.\n\n"
        "평가금액·보유수량 말고 '수익률(%)'을 읽어. "
        "반드시 JSON 배열로만 답해. 설명 금지:\n"
        '[{"name":"노보노디스크","ticker":"NVO","return_pct":-24.5},{"name":"테바","ticker":"TEVA","return_pct":102.5},{"name":"SPY","ticker":"SPY","return_pct":22.2}]'
    )))

    resp = None
    last_err = None
    for model_name in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
        success = False
        for attempt in range(3):
            try:
                resp = _client.models.generate_content(model=model_name, contents=parts)
                success = True
                break
            except Exception as e:
                last_err = e
                es = str(e)
                if "503" in es or "UNAVAILABLE" in es or "overloaded" in es.lower():
                    _time.sleep(2 * (attempt + 1))
                    continue
                else:
                    break
        if success:
            break
        if last_err and ("429" in str(last_err) or "RESOURCE_EXHAUSTED" in str(last_err)
                         or "503" in str(last_err) or "UNAVAILABLE" in str(last_err)):
            continue
        else:
            break
    if resp is None:
        return None, last_err
    try:
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip()), None
    except Exception as e:
        return None, e


def extract_holdings_from_images(image_bytes_list):
    """토스 등 포트폴리오 캡처에서 종목명과 수익률을 추출하고 티커로 변환한다.
    반환: ({"holdings": [...], "unresolved": [...]}, error)"""
    if _client is None:
        return None, "(API 키가 설정되지 않았어요)"
    from google.genai import types

    # 이미지를 한 장씩 따로 인식하면 스크롤 경계 누락이 줄어든다
    all_raw = []
    last_err = None
    for b in image_bytes_list:
        img_part = types.Part.from_bytes(data=b, mime_type="image/png")
        raw, err = _recognize_one([img_part])
        if raw:
            all_raw.extend(raw)
        elif err:
            last_err = err

    if not all_raw:
        es = str(last_err)
        if "503" in es or "UNAVAILABLE" in es:
            return None, "지금 AI 서버에 사용자가 몰려서 잠시 불안정해요. 30초쯤 후 다시 시도해주세요."
        if "429" in es or "RESOURCE_EXHAUSTED" in es:
            return None, "⏳ AI 사용량이 잠시 초과됐어요. 1분쯤 후 다시 시도해주세요."
        return None, f"이미지 인식 실패: {last_err}"

    # 티커 결정: ① 한글매핑 우선 → ② AI가 준 티커를 yfinance로 검증 → ③ 이름으로 재검색
    import yfinance as yf
    from stock_search import search_ticker, _KOREAN_MAP

    def _valid_ticker(tk):
        """티커가 실제로 존재하는지 (현재가 있으면 유효)"""
        try:
            info = yf.Ticker(tk).info
            return bool(info.get("regularMarketPrice") or info.get("currentPrice"))
        except Exception:
            return False

    seen = set()
    result = []
    unresolved = []
    for d in all_raw:
        raw_name = (d.get("name") or "").strip()
        ai_ticker = (d.get("ticker") or "").strip().upper()
        if not raw_name and not ai_ticker:
            continue

        tk = None
        # ① 이름이 영어 티커 형태면 그대로, 한글이면 매핑 검색 먼저 (매핑이 가장 신뢰도 높음)
        if raw_name:
            if len(raw_name) <= 5 and raw_name.replace("-", "").replace(".", "").isalnum() and raw_name.isascii():
                tk = raw_name.upper()
            else:
                # 한글 매핑/검색 (단, AI티커가 있으면 매핑은 한글 정확매칭만 신뢰)
                cand, _ = search_ticker(raw_name)
                if cand:
                    tk = cand
        # ② 매핑이 실패했고 AI가 티커를 줬으면, 그 티커가 실제 존재하는지 검증 후 채택
        if not tk and ai_ticker and ai_ticker != "NULL":
            if _valid_ticker(ai_ticker):
                tk = ai_ticker
        # ③ 그래도 없으면 이름으로 마지막 재검색
        if not tk and raw_name:
            cand, _ = search_ticker(raw_name)
            if cand:
                tk = cand

        if not tk:
            label = raw_name or ai_ticker
            if label and label not in unresolved:
                unresolved.append(label)
            continue
        tk = tk.upper()
        if tk in seen:
            continue
        seen.add(tk)
        result.append({"ticker": tk, "name": raw_name, "return_pct": d.get("return_pct")})
    return {"holdings": result, "unresolved": unresolved}, None


def diagnose_portfolio(summary):
    """포트폴리오 전체를 받아 '성장주 집중형, 변동성 높음' 같은 한 줄 진단을 만든다.
    summary: {avg_profit, avg_stability, avg_return, sectors[(섹터,개수)...], stocks[(이름,종합점수)...]}"""
    if _client is None:
        return "(API 키가 설정되지 않았어요)"

    sec_line = ", ".join(f"{s}({c}종목)" for s, c in summary.get("sectors", [])) or "정보 없음"
    stock_line = ", ".join(f"{nm}({sc}점)" for nm, sc in summary.get("stocks", [])[:12]) or "없음"
    ar = summary.get("avg_return")
    ar_line = f"{ar:+.1f}%" if ar is not None else "입력 안 됨"

    prompt = (
        "너는 친절한 투자 교육 도우미야. 아래는 한 개인 투자자의 포트폴리오 요약이야. "
        "이걸 보고 이 포트폴리오의 '성격'을 한국어로 진단해줘. "
        "예: '성장주에 집중된 공격형', '업종이 한쪽에 쏠려 분산이 약함', '안정성은 높지만 수익성은 평범' 같은 식으로.\n\n"
        f"- 평균 수익성 점수: {summary.get('avg_profit')}/100\n"
        f"- 평균 안정성 점수: {summary.get('avg_stability')}/100\n"
        f"- 평균 수익률: {ar_line}\n"
        f"- 업종 분포: {sec_line}\n"
        f"- 보유 종목(종합점수): {stock_line}\n\n"
        "다음을 한국어로 3~4문장으로: (1) 이 포트폴리오의 한 줄 성격 규정 "
        "(2) 업종/종목이 쏠려 있는지, 분산은 어떤지 (3) 수익성·안정성의 균형이 어떤지. "
        "제목·번호·별표 없이 자연스러운 문단으로. 전문용어는 쉽게 풀어서. "
        "특정 종목 매수/매도 추천은 절대 하지 말고, 객관적 진단만.\n"
    )
    return _simple_generate(prompt)


def summarize_insider(name, trades):
    """내부자 거래 목록을 받아 한국어로 핵심 흐름을 요약한다."""
    if _client is None:
        return "(API 키가 설정되지 않았어요)"
    if not trades:
        return "요약할 내부자 거래가 없어요."

    lines = []
    for t in trades:
        for tx in t["txns"]:
            sh = f"{tx['shares']:,}주" if tx.get("shares") else ""
            lines.append(f"- {t['date']} {t['name']}({t['title']}): {tx['label']} {sh}")
    body = "\n".join(lines)
    prompt = (
        f"아래는 '{name}' 종목의 최근 내부자(임원·이사) 거래 내역이야. "
        "이걸 보고 한국어로 다음 세 가지를 담백하게 설명해줘:\n"
        "(1) 최근 내부자들이 전반적으로 사는 쪽인지 파는 쪽인지, 누가 주요하게 거래했는지\n"
        "(2) 그렇게 거래한 이유로 '일반적으로' 어떤 것이 거론되는지 — 매수는 회사 전망에 대한 자신감일 "
        "수 있고, 매도는 세금 납부·자금 필요·자산 분산 같은 개인 사정인 경우도 많아. 단, 실제 이유는 "
        "공시에 안 나오니 반드시 '~일 수 있다'로만 말하고 단정 짓지 마.\n"
        "(3) 이런 흐름이 주가에 어떤 신호로 해석될 수 있는지 — 단, 내부자 거래는 참고 지표일 뿐 "
        "주가를 결정하지는 않는다는 점도 짧게 덧붙여.\n\n"
        "규칙: 전체 3~4문장으로 간결하게. 데이터에 없는 거래나 이유를 지어내지 마. "
        "매수/매도 추천은 하지 마. 객관적으로.\n\n" + body
    )
    return _simple_generate(prompt)


def _grounded_generate(prompt):
    """Google 검색(grounding)을 켜고 prompt를 실행한 뒤 결과를 파싱해 돌려준다.
    정책 검색/타임라인 함수가 공통으로 쓰는 내부 헬퍼.
    반환: (dict 또는 None, error)
      dict = {"text": 본문, "tickers": [티커...], "sources": [{title,uri}...], "queries": [검색어...]}
    프롬프트는 맨 마지막 줄에 'TICKERS: AAPL, NVDA' 형식의 티커 줄을 포함해야 한다.
    """
    if _client is None:
        return None, "(API 키가 설정되지 않았어요)"
    from google.genai import types
    import re

    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    cfg = types.GenerateContentConfig(tools=[grounding_tool])

    resp = None
    last_err = None
    # 추론 품질이 중요하므로 flash 우선, 과부하/한도 시 flash-lite 폴백 (둘 다 grounding 지원)
    for model_name in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
        try:
            resp = _client.models.generate_content(
                model=model_name, contents=prompt, config=cfg)
            break
        except Exception as e:
            last_err = e
            es = str(e)
            if any(k in es for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")) \
               or "overloaded" in es.lower():
                continue
            break
    if resp is None:
        return None, _friendly_error(last_err)

    try:
        raw = (resp.text or "").strip()
    except Exception as e:
        return None, _friendly_error(e)
    if not raw:
        return None, "AI가 빈 응답을 줬어요. 잠시 후 다시 시도해주세요."

    # ── TICKERS 줄 분리/파싱 (형식: 'TICKERS: AAPL | Apple; NVDA | NVIDIA') ──
    tickers, ticker_names, body_lines = [], {}, []
    for line in raw.splitlines():
        if line.strip().upper().startswith("TICKERS:"):
            after = line.split(":", 1)[1] if ":" in line else ""
            for item in after.split(";"):
                item = item.strip()
                if not item:
                    continue
                if "|" in item:
                    tk_part, nm_part = item.split("|", 1)
                else:
                    tk_part, nm_part = item, ""
                t = tk_part.strip().upper().lstrip("$")
                nm = nm_part.strip()
                if (t and t not in ("없음", "NONE")
                        and t.replace(".", "").replace("-", "").isalnum()
                        and t.isascii() and len(t) <= 5 and t not in tickers):
                    tickers.append(t)
                    if nm:
                        ticker_names[t] = nm
        else:
            body_lines.append(line)
    body = "\n".join(body_lines).strip()

    # ── 출처(grounding) 추출 ─────────────────────────────
    sources, queries = [], []
    try:
        for cand in (resp.candidates or []):
            gm = getattr(cand, "grounding_metadata", None)
            if not gm:
                continue
            for q in (getattr(gm, "web_search_queries", None) or []):
                if q and q not in queries:
                    queries.append(q)
            for ch in (getattr(gm, "grounding_chunks", None) or []):
                web = getattr(ch, "web", None)
                if web and getattr(web, "uri", None):
                    title = getattr(web, "title", "") or web.uri
                    sources.append({"title": title, "uri": web.uri})
    except Exception:
        pass
    seen, uniq = set(), []
    for s in sources:
        if s["uri"] not in seen:
            seen.add(s["uri"])
            uniq.append(s)

    return {
        "text": body,
        "tickers": tickers[:8],
        "ticker_names": ticker_names,
        "sources": uniq[:8],
        "queries": queries[:8],
    }, None


def analyze_government_policy(focus=""):
    """웹검색으로 현 미국 정부·대통령의 최근 정책 동향과 영향받을 수 있는 산업/섹터,
    정책과 직접 관련된 종목 후보를 분석한다. 정치 중립 + 투자 추천 없음.
    반환: (dict 또는 None, error)  — dict 형식은 _grounded_generate 참고."""
    if _client is None:
        return None, "(API 키가 설정되지 않았어요)"

    focus_line = (
        f"\n사용자가 특히 관심 있는 분야/키워드: {focus.strip()}\n"
        "→ 이 분야와 관련된 정책에 좀 더 비중을 두되, 다른 중요한 동향도 함께 다뤄.\n"
        if focus and focus.strip() else "\n"
    )
    prompt = (
        "너는 정치적으로 철저히 중립적인 '투자 교육 도우미'야. "
        "Google 검색을 적극 활용해서, 현재 미국 정부와 대통령의 '최근(가능한 한 최신)' "
        "정책·행정명령·주요 발언 동향을 조사하고, 그것이 어떤 산업/섹터에 영향을 줄 수 있는지 "
        "한국 주식 초보자도 이해할 수 있게 한국어로 분석해줘."
        + focus_line +
        "\n아래 순서로, 자연스러운 문단들로만 작성해(제목·번호·별표·#·마크다운 기호 절대 금지):\n"
        "- 첫째: 최근 미국 정부의 핵심 정책/발언 동향 2~3가지. 각각 '언제, 무슨 내용인지' 구체적으로. "
        "(검색으로 날짜와 사실을 확인해서 적어)\n"
        "- 둘째: 그 정책들이 영향을 줄 수 있는 산업/섹터는 무엇이고, 왜 그런지. "
        "수혜가 거론되는 쪽과 부담이 거론되는 쪽을 균형 있게.\n"
        "- 셋째: 주의할 점. 정책은 언제든 바뀔 수 있고, 주가 영향은 불확실하며, 이 분석은 교육용일 뿐이라는 점.\n\n"
        "반드시 지킬 규칙:\n"
        "1) 특정 정당·정치인을 옹호하거나 비난하지 마. 가치판단 없이 '사실'과 '거론되는 영향'만 담백하게.\n"
        "2) 매수/매도 추천은 절대 하지 마. '수혜 가능성이 거론된다', '관련 종목으로 언급된다' 같은 객관적 표현만 써.\n"
        "3) 검색으로 확인되지 않은 내용은 지어내지 마. 불확실하면 솔직히 '확인되지 않았다'고 해.\n"
        "4) 전문용어는 쉬운 말로 풀어서 설명해. 한국어 존댓말로, 친근하지만 정확하게.\n"
        "5) 분석의 '맨 마지막 줄'에만, 본문에서 언급한 '미국 증시 상장사' 중 정책과 직접 관련된 종목을 "
        "정확히 이 형식으로 한 줄 적어 (티커와 짧은 영어 회사명을 막대기 '|'로, 종목끼리는 세미콜론 ';'로 구분):\n"
        "TICKERS: AAPL | Apple; NVDA | NVIDIA; INTC | Intel\n"
        "(최대 8개, ETF·지수는 제외, 관련 종목이 마땅치 않으면 'TICKERS: 없음'.)\n"
    )
    return _grounded_generate(prompt)


def analyze_sector_policy_timeline(sector):
    """웹검색으로 특정 분야에 대한 미국 정부의 최근 약 4년간 정책/발언을
    '최신 → 과거' 타임라인으로 정리하고, 정부가 무엇을 밀어주는지와 관련 회사/종목을 설명한다.
    정치 중립 + 투자 추천 없음.
    반환: (dict 또는 None, error)  — dict 형식은 _grounded_generate 참고."""
    if _client is None:
        return None, "(API 키가 설정되지 않았어요)"
    from datetime import datetime
    this_year = datetime.now().year

    prompt = (
        "너는 정치적으로 철저히 중립적인 '투자 교육 도우미'야. "
        f"Google 검색을 적극 활용해서, 미국 정부와 대통령이 '{sector}' 분야에 대해 "
        f"최근 약 4년간({this_year-4}년부터 {this_year}년까지) 어떤 정책·행정명령·주요 발언을 했는지 조사하고, "
        "그것이 이 분야와 관련 기업에 어떤 영향을 줬는지(또는 줄 수 있는지) "
        "한국 주식 초보자도 이해하게 한국어로 정리해줘.\n\n"
        "형식 — '최신 → 과거' 순서의 타임라인처럼 작성해. 각 항목을 다음처럼 한 문단씩:\n"
        f"[{this_year}년 O월] 무슨 정책/발언이 있었는지 → 그게 이 분야에 어떤 영향을 줬는지(또는 줄 수 있는지)\n"
        "[2025년 O월] ...\n"
        "이렇게 시기를 대괄호로 표시하고, 검색으로 확인된 사건 위주로 4~7개 정도 적어. "
        "(제목·번호·별표·# 기호는 쓰지 마. 시기는 검색으로 확인해 정확히.)\n\n"
        "타임라인 뒤에 마지막 문단으로, '그래서 미국 정부가 이 분야에서 무엇을 밀어주는 흐름인지, "
        "그리고 어떤 회사/종목이 그 흐름과 관련해 거론되는지'를 2~3문장으로 정리해줘.\n\n"
        "반드시 지킬 규칙:\n"
        "1) 특정 정당·정치인을 옹호/비난하지 마. 사실과 거론되는 영향만 담백하게.\n"
        "2) 매수/매도 추천 금지. '수혜 가능성이 거론된다' 같은 객관적 표현만.\n"
        "3) 검색으로 확인되지 않은 내용은 지어내지 마. 모르면 솔직히 말해.\n"
        "4) 전문용어는 쉬운 말로. 한국어 존댓말로.\n"
        "5) 맨 마지막 줄에만 관련 '미국 증시 상장사'를 이 형식으로 (티커와 짧은 영어 회사명을 '|'로, "
        "종목끼리는 세미콜론 ';'로 구분):\n"
        "TICKERS: AAPL | Apple; NVDA | NVIDIA\n"
        "(최대 8개, ETF·지수 제외, 없으면 'TICKERS: 없음').\n"
    )
    return _grounded_generate(prompt)

def analyze_remarks_overview():
    """웹검색으로 현 미국 대통령의 '최근 주요 발언'을 분야별로 묶어 한눈에 정리한다.
    출처가 확인된 발언만 다루고, 정치 중립 + 투자 추천 없음.
    반환: (dict 또는 None, error) — dict 형식은 _grounded_generate 참고."""
    if _client is None:
        return None, "(API 키가 설정되지 않았어요)"
    prompt = (
        "너는 정치적으로 철저히 중립적인 '투자 교육 도우미'야. "
        "Google 검색을 적극 활용해서, '현재' 미국 대통령이 '최근(가능한 한 최신)' 공개적으로 한 "
        "주요 발언들을 찾아, 산업·경제와 관련된 것 위주로 분야별로 묶어 한국어로 정리해줘.\n\n"
        "형식 — 발언이 실제로 확인된 분야만 골라, 각 분야를 이렇게 써:\n"
        "【분야명】\n"
        "그 분야에 대해 대통령이 '언제, 무슨 취지로' 말했는지 1~2문장. 핵심 표현은 짧게 따옴표로 인용해도 되지만 "
        "한 발언당 한 문장 이내로만. → 그 발언이 어떤 산업·기업에 영향이 거론되는지 한 문장.\n\n"
        "다룰 수 있는 분야 예시: 반도체, AI 인프라, 에너지, 방산·국방, 제약·바이오, 관세·무역, 암호화폐, 전기차·배터리, 금리·세금 등.\n"
        "(분야는 4~7개, 확인된 것만. 제목·번호·별표·# 기호는 쓰지 말고 위 【분야명】 표기만 사용.)\n\n"
        "반드시 지킬 규칙:\n"
        "1) 특정 정당·정치인을 옹호하거나 비난하지 마. 가치판단 없이 '무슨 말을 했다는 사실'과 '거론되는 영향'만 담백하게.\n"
        "2) 매수/매도 추천은 절대 하지 마. '수혜 가능성이 거론된다' 같은 객관적 표현만.\n"
        "3) ★검색으로 출처가 확인된 발언만 적어. 확인 안 되면 지어내지 말고 그 분야는 빼.★ "
        "인터넷에는 가짜·왜곡 인용도 많으니, 신뢰할 만한 출처로 교차 확인된 것만 담아.\n"
        "4) 긴 문장을 그대로 길게 베끼지 말고, 핵심만 짧게 인용하거나 네 말로 바꿔 써(저작권).\n"
        "5) 전문용어는 쉬운 말로 풀어서. 한국어 존댓말로, 친근하지만 정확하게.\n"
        "6) 분석의 '맨 마지막 줄'에만, 본문에서 언급한 '미국 증시 상장사'를 정확히 이 형식으로 한 줄 "
        "(티커와 짧은 영어 회사명을 막대기 '|'로, 종목끼리는 세미콜론 ';'로 구분):\n"
        "TICKERS: NVDA | NVIDIA; INTC | Intel\n"
        "(최대 8개, ETF·지수는 제외, 관련 종목이 마땅치 않으면 'TICKERS: 없음'.)\n"
    )
    return _grounded_generate(prompt)


def analyze_remarks_sector(sector):
    """웹검색으로 현 미국 대통령이 특정 분야에 대해 한 발언들을 '최신 → 과거' 순서로
    날짜·출처와 함께 모아 정리한다. 출처가 확인된 발언만, 정치 중립 + 투자 추천 없음.
    반환: (dict 또는 None, error) — dict 형식은 _grounded_generate 참고."""
    if _client is None:
        return None, "(API 키가 설정되지 않았어요)"
    from datetime import datetime
    this_year = datetime.now().year
    prompt = (
        "너는 정치적으로 철저히 중립적인 '투자 교육 도우미'야. "
        f"Google 검색을 적극 활용해서, '현재' 미국 대통령이 '{sector}' 분야에 대해 "
        f"최근 몇 년간({this_year-3}년부터 {this_year}년까지) 공개적으로 한 발언들을 찾아, "
        "'최신 → 과거' 순서로 한국어로 정리해줘.\n\n"
        "형식 — 각 발언을 이렇게 한 항목씩:\n"
        f"[{this_year}년 O월] 어떤 자리·맥락에서 무슨 말을 했는지. 핵심 표현은 짧게 따옴표로 인용 가능(한 문장 이내). "
        "→ 그게 이 분야·관련 기업에 어떤 영향이 거론되는지 한 문장.\n"
        "[2025년 O월] ...\n"
        "이렇게 시기를 대괄호로 표시하고, 검색으로 확인된 발언 위주로 4~7개 적어. "
        "(제목·번호·별표·# 기호는 쓰지 마. 시기는 검색으로 확인해 정확히.)\n\n"
        "발언들 뒤에 마지막 문단으로, '이 발언들을 종합하면 대통령이 이 분야에서 어떤 방향을 시사하는지, "
        "그리고 어떤 회사·종목이 그와 관련해 거론되는지'를 2~3문장으로 정리해줘.\n\n"
        "반드시 지킬 규칙:\n"
        "1) 특정 정당·정치인을 옹호하거나 비난하지 마. 사실과 거론되는 영향만 담백하게.\n"
        "2) 매수/매도 추천 금지. '수혜 가능성이 거론된다' 같은 객관적 표현만.\n"
        "3) ★검색으로 출처가 확인된 발언만. 확인 안 되면 지어내지 마.★ 인터넷엔 가짜 인용이 많으니 교차 확인된 것만.\n"
        "4) 긴 문장을 길게 베끼지 말고 핵심만 짧게 인용하거나 네 말로 바꿔 써(저작권).\n"
        "5) 전문용어는 쉬운 말로. 한국어 존댓말로.\n"
        "6) 맨 마지막 줄에만 관련 '미국 증시 상장사'를 이 형식으로 (티커와 짧은 영어 회사명을 '|'로, "
        "종목끼리는 세미콜론 ';'로 구분):\n"
        "TICKERS: NVDA | NVIDIA\n"
        "(최대 8개, ETF·지수 제외, 없으면 'TICKERS: 없음').\n"
    )
    return _grounded_generate(prompt)


def analyze_trending_sectors():
    """웹검색으로 '요즘 미국 증시에서 관심·화제가 집중되는 분야'를 순위로 정리하고,
    각 분야에서 많이 거론되는 종목을 함께 보여준다. 추천이 아니라 '화제성' 정리. 정치 중립.
    반환: (dict 또는 None, error) — dict 형식은 _grounded_generate 참고."""
    if _client is None:
        return None, "(API 키가 설정되지 않았어요)"
    prompt = (
        "너는 '투자 교육 도우미'야. Google 검색을 적극 활용해서, '지금(가능한 한 최신)' 미국 증시에서 "
        "투자자·언론의 관심과 화제가 가장 많이 쏠리는 분야(테마)를 찾아 순위로 정리해줘. "
        "한국 주식 초보자도 이해하게 한국어로.\n\n"
        "형식 — 관심이 많은 순서대로 5~7개 분야를 이렇게 써:\n"
        "【1위 · 분야명】\n"
        "이 분야가 '왜' 요즘 화제인지(어떤 뉴스·이슈 때문인지) 1~2문장. → 이 분야에서 많이 거론되는 대표 종목 몇 개를 이름으로 언급.\n"
        "【2위 · 분야명】\n"
        "...\n\n"
        "(제목·번호·별표·# 기호는 쓰지 말고 위 【순위 · 분야명】 표기만 사용.)\n\n"
        "반드시 지킬 규칙:\n"
        "1) ★이건 '추천'이 아니라 '요즘 화제가 되는 것'을 정리하는 거야. 사거나 팔라는 말은 절대 하지 마.★\n"
        "2) ★중요: 관심이 많다고 좋은 투자라는 뜻이 아니야.★ 오히려 화제가 몰린 분야는 이미 가격이 많이 올라 "
        "고평가·과열일 수 있어. 이 점을 맨 마지막에 꼭 한 문장으로 덧붙여.\n"
        "3) 검색으로 확인된 사실 위주로. 확인 안 되면 지어내지 마.\n"
        "4) 특정 정당·정치인 옹호/비난 금지. 전문용어는 쉬운 말로. 한국어 존댓말로.\n"
        "5) 맨 마지막 줄에만, 본문에서 언급한 '미국 증시 상장사'를 이 형식으로 (티커와 짧은 영어 회사명을 '|'로, "
        "종목끼리는 세미콜론 ';'로 구분):\n"
        "TICKERS: NVDA | NVIDIA; PLTR | Palantir\n"
        "(최대 8개, 없으면 'TICKERS: 없음'.)\n"
    )
    return _grounded_generate(prompt)


def analyze_sector_focus(sector):
    """웹검색으로 사용자가 직접 고른 분야에서 '요즘 관심받는 종목과 그 이유'를 정리한다.
    추천이 아니라 화제성 정리. 정치 중립. 반환: (dict 또는 None, error)."""
    if _client is None:
        return None, "(API 키가 설정되지 않았어요)"
    prompt = (
        "너는 '투자 교육 도우미'야. Google 검색을 적극 활용해서, 미국 증시의 "
        f"'{sector}' 분야에서 '요즘(가능한 한 최신)' 투자자·언론의 관심이 쏠리는 대표 종목들을 찾아, "
        "한국 주식 초보자도 이해하게 한국어로 정리해줘.\n\n"
        "형식 — 자연스러운 문단으로(제목·번호·별표·# 기호 금지):\n"
        f"먼저 '{sector}' 분야가 지금 어떤 상황인지(무슨 이슈로 주목받는지) 2~3문장.\n"
        "그다음 이 분야에서 많이 거론되는 대표 종목 3~6개를 '회사이름 — 왜 거론되는지 한 문장'으로 풀어줘.\n\n"
        "반드시 지킬 규칙:\n"
        "1) ★추천이 아니라 '요즘 화제'를 정리하는 거야. 사거나 팔라는 말 금지.★\n"
        "2) ★관심이 많다고 좋은 투자라는 뜻이 아니야.★ 화제가 몰리면 이미 비쌀(고평가) 수 있다는 점을 마지막에 한 문장으로 덧붙여.\n"
        "3) 검색으로 확인된 사실 위주로. 확인 안 되면 지어내지 마.\n"
        "4) 특정 정당·정치인 옹호/비난 금지. 전문용어는 쉬운 말로. 한국어 존댓말로.\n"
        "5) 맨 마지막 줄에만 본문에서 언급한 '미국 증시 상장사'를 이 형식으로 (티커·짧은 영어명을 '|'로, 종목끼리 ';'로):\n"
        "TICKERS: NVDA | NVIDIA\n"
        "(최대 8개, 없으면 'TICKERS: 없음'.)\n"
    )
    return _grounded_generate(prompt)


def analyze_holding_thesis(name, ticker, holders=None, score=None, news=None):
    """스마트머니가 보유한 종목에 대해 '왜 이런 큰손들이 들고 있을지(데이터 근거)'와
    '앞으로의 전망(데이터+뉴스 기반, 거론되는 시나리오)'을 정리한다. 추천 아님, 중립.
    holders: 보유 투자자 이름 리스트, score: score_stock 결과 dict, news: get_news 결과 리스트.
    반환: (dict 또는 None, error)."""
    if _client is None:
        return None, "(API 키가 설정되지 않았어요)"
    holders = holders or []
    data_bits = []
    if score:
        if score.get("profit_score") is not None:
            data_bits.append(f"수익성 점수 {score['profit_score']}/100")
        if score.get("stability_score") is not None:
            data_bits.append(f"안정성 점수 {score['stability_score']}/100")
        if score.get("per") is not None:
            data_bits.append(f"PER {score['per']}")
        if score.get("upside_pct") is not None:
            data_bits.append(f"애널리스트 목표가 상승여력 {score['upside_pct']}%")
        if score.get("dividend_yield") is not None:
            data_bits.append(f"배당수익률 {score['dividend_yield']}%")
        if score.get("analyst_rec"):
            data_bits.append(f"애널리스트 의견 {score['analyst_rec']}")
        if score.get("sector"):
            data_bits.append(f"업종 {score['sector']}")
    data_line = "; ".join(data_bits) if data_bits else "(지표 데이터 부족)"
    news_titles = [n.get("title", "") for n in (news or [])[:5] if n.get("title")]
    news_line = " / ".join(news_titles) if news_titles else "없음"
    holder_line = ", ".join(holders[:6]) if holders else "여러 유명 기관"

    prompt = (
        "너는 종목·정치에 중립적인 '투자 교육 도우미'야. Google 검색도 활용해서 "
        f"미국 상장사 '{name}'({ticker})에 대해, 한국 주식 초보자도 이해하게 한국어로 정리해줘.\n\n"
        f"참고 — 이 종목을 보유한 유명 투자자/기관: {holder_line}\n"
        f"이 앱이 계산한 지표: {data_line}\n"
        f"최근 뉴스 제목: {news_line}\n\n"
        "아래 두 가지를 자연스러운 문단으로 써(제목·번호·별표·# 기호 금지, 각 묶음 앞에만 【 】 표기 사용):\n"
        "【왜 보유】 이런 큰손들이 이 회사를 들고 있는 '이유로 거론되는' 점들. 이 회사가 뭘로 돈을 버는지, "
        "강점(해자)·재무·성장성 등을 위 지표와 검색으로 확인된 사실 위주로. 추측이면 추측이라고 밝혀.\n"
        "【전망】 데이터와 최근 뉴스가 가리키는 앞으로의 그림. 긍정적으로 거론되는 점과 위험·우려로 거론되는 점을 "
        "'균형 있게'. 확정적 예측처럼 말하지 말고 '거론된다/가능성이 있다'로 표현해.\n\n"
        "반드시 지킬 규칙:\n"
        "1) ★매수·매도 추천 절대 금지.★ 큰손이 샀다는 게 '좋다'는 뜻이 아니고, 13F는 분기 뒤 공시라 "
        "지금은 이미 팔았을 수도 있다는 점을 꼭 한 번 짚어줘.\n"
        "2) 검색·지표로 확인 안 된 건 지어내지 마. 모르면 솔직히 말해.\n"
        "3) 전문용어는 쉬운 말로 풀어서. 한국어 존댓말로.\n"
        "4) 맨 마지막 줄에 'TICKERS: 없음'이라고만 적어.\n"
    )
    return _grounded_generate(prompt)
