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

    try:
        resp = _client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        return resp.text.strip()
    except Exception as e:
        return _friendly_error(e)


def summarize_news(name, news_items):
    """뉴스 제목 목록을 받아 한국어로 핵심을 요약한다."""
    if _client is None:
        return "(API 키가 설정되지 않았어요)"
    if not news_items:
        return "요약할 뉴스가 없어요."

    titles = "\n".join(f"- {n['title']} ({n.get('publisher','')})" for n in news_items)
    prompt = (
        f"아래는 '{name}' 종목과 관련된 최근 영어 뉴스 제목들이야. "
        "이걸 바탕으로 이 종목을 둘러싼 최근 분위기와 핵심 이슈를 "
        "한국어로 3~4문장으로 요약해줘. 투자 추천은 하지 말고, "
        "어떤 주제의 뉴스가 많은지 흐름 위주로 담백하게 정리해줘.\n\n" + titles
    )
    try:
        resp = _client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        return resp.text.strip()
    except Exception as e:
        return _friendly_error(e)


def extract_holdings_from_images(image_bytes_list):
    """토스 등 포트폴리오 캡처 이미지들에서 종목 티커와 수익률을 추출한다.
    반환: [{"ticker": "...", "name": "...", "return_pct": float|None}, ...]"""
    if _client is None:
        return None, "(API 키가 설정되지 않았어요)"
    from google.genai import types
    import json

    parts = []
    for b in image_bytes_list:
        parts.append(types.Part.from_bytes(data=b, mime_type="image/png"))
    parts.append(types.Part.from_text(text=(
        "이 이미지들은 한국 증권 앱(토스 등)의 해외주식 포트폴리오 화면 캡처야. "
        "화면에 보이는 모든 종목을 빠짐없이 읽어줘. 각 종목마다 다음을 추출해:\n"
        "(1) 미국 주식 티커 심볼 (대문자). 화면에 티커가 안 보이면 종목 이름으로 정확한 미국 티커를 추론해.\n"
        "(2) 종목 이름 (보이는 그대로)\n"
        "(3) 총 수익률(%) — 토스는 빨강이 +수익, 파랑이 -손실이야. 부호를 정확히 반영해. 숫자만, 못 읽으면 null.\n\n"
        "주의사항:\n"
        "- 같은 종목이 여러 번 나오면 한 번만. 중복 금지.\n"
        "- 여러 장의 캡처는 스크롤한 화면이라 위아래가 겹치거나 잘릴 수 있어. 이미지 맨 위·맨 아래에 일부만 보이는 종목도 빠짐없이 포함해.\n"
        "- 티커가 확실하지 않으면 가장 널리 알려진 미국 상장 보통주 티커를 써. (예: 구글->GOOGL, 버크셔->BRK-B)\n"
        "- 평가금액·보유수량이 아니라 반드시 '총 수익률(%)'을 읽어. 토스에서 '총 수익' 칸의 퍼센트 숫자야.\n"
        "- 한국 주식(삼성전자 등)이나 코인은 제외하고 미국 주식만.\n\n"
        "반드시 아래 JSON 배열 형식으로만 답해. 다른 설명 절대 금지:\n"
        '[{"ticker":"NVDA","name":"엔비디아","return_pct":17.3},{"ticker":"AAPL","name":"애플","return_pct":-5.2}]'
    )))

    try:
        resp = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=parts,
        )
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        # 중복 티커 제거 (첫 번째만 유지)
        seen = set()
        deduped = []
        for d in data:
            tk = (d.get("ticker") or "").strip().upper()
            if tk and tk not in seen:
                seen.add(tk)
                d["ticker"] = tk
                deduped.append(d)
        return deduped, None
    except Exception as e:
        return None, f"이미지 인식 실패: {e}"


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
        "이걸 보고 최근 내부자들의 움직임을 한국어로 3~4문장으로 요약해줘. "
        "매수가 많은지 매도가 많은지, 누가 주요하게 거래했는지 짚어주되, "
        "매도는 세금·개인사정 등 이유가 다양하니 단정하지 말고, "
        "투자 추천은 하지 마. 담백하고 객관적으로.\n\n" + body
    )
    try:
        resp = _client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        return resp.text.strip()
    except Exception as e:
        return _friendly_error(e)
