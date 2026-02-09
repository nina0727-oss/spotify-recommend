from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from services.openai_service import OpenAIService, StrategyResult
from services.spotify_service import SpotifyService, TrackRow
from utils.prompt_templates import build_strategy_prompt

# -----------------------------
# Secrets / Config
# -----------------------------
REQUIRED_SECRET_KEYS = (
    "OPENAI_API_KEY",
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
)


def load_secrets() -> Dict[str, str]:
    """
    Streamlit Cloud 친화 로딩 우선순위:
    1) st.secrets (Cloud)
    2) .env (local fallback)
    """
    # 1) st.secrets 우선
    secrets: Dict[str, str] = {}
    for k in REQUIRED_SECRET_KEYS:
        v = st.secrets.get(k) if hasattr(st, "secrets") else None
        if v:
            secrets[k] = str(v)

    # 2) .env fallback
    if len(secrets) < len(REQUIRED_SECRET_KEYS):
        try:
            from dotenv import load_dotenv
            import os

            load_dotenv()
            for k in REQUIRED_SECRET_KEYS:
                if k not in secrets:
                    v = os.getenv(k)
                    if v:
                        secrets[k] = v
        except Exception:
            # dotenv 미설치/미사용 환경 등: 조용히 패스
            pass

    return secrets


def validate_secrets(secrets: Dict[str, str]) -> Tuple[bool, List[str]]:
    missing = [k for k in REQUIRED_SECRET_KEYS if not secrets.get(k)]
    return (len(missing) == 0, missing)


# -----------------------------
# Cached service factories
# -----------------------------
@st.cache_resource(show_spinner=False)
def get_openai_service(api_key: str) -> OpenAIService:
    return OpenAIService(api_key=api_key)


@st.cache_resource(show_spinner=False)
def get_spotify_service(client_id: str, client_secret: str) -> SpotifyService:
    return SpotifyService(client_id=client_id, client_secret=client_secret)


# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="음악 플리 추천", page_icon="🎵", layout="wide")

st.title("🎵 음악 플리 추천")
st.caption("기분/상황 기반 AI+Spotify 추천")

secrets = load_secrets()
ok, missing = validate_secrets(secrets)

with st.sidebar:
    st.header("⚙️ 설정")

    model = st.selectbox(
        "OpenAI 모델 선택",
        options=[
            "gpt-4o-mini",
            "gpt-4o",
        ],
        index=0,
        help="응답은 JSON only로 받습니다.",
    )

    n_tracks = st.slider("추천 곡 수", min_value=5, max_value=30, value=10, step=1)

    market = st.selectbox(
        "시장 코드",
        options=["KR", "US", "JP"],
        index=0,
        help="Spotify 검색 market 파라미터로 적용됩니다.",
    )

    allow_explicit = st.toggle("Explicit 허용 여부", value=False)

    if st.button("🔄 설정 초기화"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

if not ok:
    st.error(
        "필수 Secrets가 누락되었습니다. 아래 키를 설정하세요:\n\n"
        + "\n".join([f"- {k}" for k in missing])
    )
    st.info("Streamlit Cloud에서는 Advanced settings → Secrets에 등록하세요. (README 참고)")
    st.stop()

# Session defaults
st.session_state.setdefault("mood_text", "")
st.session_state.setdefault("context_text", "")
st.session_state.setdefault("genres", [])
st.session_state.setdefault("energy", 5)
st.session_state.setdefault("tone", "밝고 신나는")
st.session_state.setdefault("last_strategy", None)
st.session_state.setdefault("last_tracks", None)

col1, col2 = st.columns(2)

with col1:
    mood_text = st.text_input("오늘의 기분", value=st.session_state["mood_text"], placeholder="예: 설레고 들떠요 / 무기력해요")
    context_text = st.text_input(
        "현재 상황/활동",
        value=st.session_state["context_text"],
        placeholder="예: 등굣길 / 공부 중 / 운동 / 야근 / 드라이브",
    )

with col2:
    genres = st.multiselect(
        "선호 장르",
        options=[
            "k-pop",
            "pop",
            "hip-hop",
            "r&b",
            "rock",
            "indie",
            "edm",
            "j-pop",
            "lofi",
            "jazz",
            "classical",
            "metal",
            "acoustic",
        ],
        default=st.session_state["genres"],
    )
    energy = st.slider("에너지 레벨 (1~10)", 1, 10, int(st.session_state["energy"]))
    tone = st.selectbox(
        "감정 톤",
        options=[
            "밝고 신나는",
            "차분하고 안정적인",
            "감성적이고 잔잔한",
            "강렬하고 공격적인",
            "몽환적이고 판타지한",
            "코믹/가벼운",
        ],
        index=[
            "밝고 신나는",
            "차분하고 안정적인",
            "감성적이고 잔잔한",
            "강렬하고 공격적인",
            "몽환적이고 판타지한",
            "코믹/가벼운",
        ].index(st.session_state["tone"]),
    )

st.divider()

run = st.button("✨ 플리 추천 받기", type="primary", use_container_width=True)

if run:
    st.session_state["mood_text"] = mood_text
    st.session_state["context_text"] = context_text
    st.session_state["genres"] = genres
    st.session_state["energy"] = energy
    st.session_state["tone"] = tone

    openai_svc = get_openai_service(secrets["OPENAI_API_KEY"])
    spotify_svc = get_spotify_service(secrets["SPOTIFY_CLIENT_ID"], secrets["SPOTIFY_CLIENT_SECRET"])

    prompt = build_strategy_prompt(
        mood_text=mood_text,
        context_text=context_text,
        preferred_genres=genres,
        energy=energy,
        tone=tone,
        market=market,
        allow_explicit=allow_explicit,
        n_tracks=n_tracks,
    )

    with st.spinner("AI가 추천 전략을 만들고 있어요..."):
        try:
            strategy: StrategyResult = openai_svc.generate_strategy_json(
                model=model,
                prompt=prompt,
                max_retries=2,
            )
            st.session_state["last_strategy"] = asdict(strategy)
        except Exception as e:
            st.error("AI 전략 생성에 실패했습니다. 입력을 조금 바꾸거나 잠시 후 다시 시도해 주세요.")
            st.exception(e)
            st.stop()

    with st.spinner("Spotify에서 곡을 찾는 중..."):
        try:
            tracks: List[TrackRow] = spotify_svc.search_tracks_from_strategy(
                strategy=strategy,
                market=market,
                target_count=n_tracks,
                allow_explicit=allow_explicit,
            )
            st.session_state["last_tracks"] = [t.to_dict() for t in tracks]
        except Exception as e:
            st.error("Spotify 검색에 실패했습니다. 인증/Secrets/market 설정을 확인해 주세요.")
            st.exception(e)
            st.stop()

# -----------------------------
# Render Results (session_state 유지)
# -----------------------------
strategy_data: Optional[Dict[str, Any]] = st.session_state.get("last_strategy")
tracks_data: Optional[List[Dict[str, Any]]] = st.session_state.get("last_tracks")

if strategy_data:
    st.subheader("🧠 AI 해석 카드")
    c1, c2 = st.columns([2, 1])

    with c1:
        st.markdown(
            f"""
            <div style="padding:16px;border-radius:16px;border:1px solid rgba(255,255,255,0.15);">
              <div style="font-size:18px;font-weight:700;margin-bottom:8px;">{strategy_data.get("playlist_theme","")}</div>
              <div style="opacity:0.9;"><b>요약</b>: {strategy_data.get("mood_summary","")}</div>
              <div style="opacity:0.9;margin-top:6px;"><b>이유</b>: {strategy_data.get("reason","")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.write("**keywords**")
        st.write(strategy_data.get("keywords", []))
        st.write("**seed_genres**")
        st.write(strategy_data.get("seed_genres", []))

    st.download_button(
        label="⬇️ 전략 JSON 다운로드",
        data=json.dumps(strategy_data, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="playlist_strategy.json",
        mime="application/json",
        use_container_width=True,
    )

if tracks_data:
    st.subheader("🎧 추천 곡")
    # 순번 컬럼 보장
    table_rows = []
    for i, row in enumerate(tracks_data, start=1):
        row = dict(row)
        row["순번"] = i
        table_rows.append(
            {
                "순번": row["순번"],
                "곡명": row.get("track_name", ""),
                "아티스트": row.get("artist_name", ""),
                "앨범": row.get("album_name", ""),
                "preview_url": row.get("preview_url", "미리듣기 없음"),
                "spotify_url": row.get("spotify_url", ""),
            }
        )

    st.dataframe(
        table_rows,
        use_container_width=True,
        hide_index=True,
    )
