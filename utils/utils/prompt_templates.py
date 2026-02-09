from __future__ import annotations

from typing import List


def build_strategy_prompt(
    mood_text: str,
    context_text: str,
    preferred_genres: List[str],
    energy: int,
    tone: str,
    market: str,
    allow_explicit: bool,
    n_tracks: int,
) -> str:
    # “한국어 입력 최적화” + “장르 다양성 확보 규칙”을 프롬프트에 명시
    preferred = preferred_genres if preferred_genres else ["(없음)"]

    return f"""
너는 음악 플레이리스트 큐레이터다. 사용자의 한국어 입력을 바탕으로 Spotify에서 곡을 찾기 위한 "검색 전략"을 생성한다.
아래 JSON 스키마를 **정확히** 만족하는 **JSON 객체만** 출력하라(설명/마크다운/코드블록 금지).

[사용자 입력]
- 오늘의 기분: {mood_text}
- 현재 상황/활동: {context_text}
- 선호 장르(선택): {preferred}
- 에너지 레벨(1~10): {energy}
- 감정 톤: {tone}
- market: {market}
- explicit 허용: {allow_explicit}
- 목표 곡 수: {n_tracks}

[장르 다양성 확보 규칙]
- seed_genres는 2~5개.
- 사용자가 장르를 선택했으면 그 안에서 시작하되, 시장({market}) 기준으로 너무 한 장르에 치우치지 않게 1~2개는 인접 장르로 확장.
- 무조건 "k-pop"만 고정하지 말고 상황/에너지에 따라 pop, r&b, edm, indie 등으로 분산.
- seed_genres는 Spotify 장르 문자열처럼 간단한 소문자/하이픈 형태로.

[검색 쿼리 생성 규칙]
- search_queries는 6~12개.
- Spotify 검색에 유리하도록 짧고 명확한 조합을 섞어라:
  - mood/상황 키워드(한국어/영어 혼합 가능)
  - 장르
  - 템포/에너지(예: upbeat, chill, energetic, focus, workout 등)
- 동일한 의미의 쿼리는 중복하지 말 것.
- explicit 허용이 false이면, 가급적 "clean" 또는 "non explicit" 성격을 암시하는 키워드를 1~2개 섞어라(단 과도하게 반복 금지).

[반드시 출력할 JSON 스키마]
{{
  "mood_summary": "...",
  "keywords": ["..."],
  "seed_genres": ["pop", "k-pop"],
  "search_queries": ["..."],
  "playlist_theme": "...",
  "reason": "..."
}}

추가 조건:
- mood_summary, playlist_theme, reason은 자연스러운 한국어로.
- keywords는 5~10개. (한국어 중심 + 필요 시 영어 1~3개)
""".strip()
