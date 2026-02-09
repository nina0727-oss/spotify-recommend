 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/app.py b/app.py
index 8b137891791fe96927ad78e64b0aad7bded08bdc..ec9bdd427380eb71f53e1c8310693ed679c94413 100644
--- a/app.py
+++ b/app.py
@@ -1 +1,173 @@
+from __future__ import annotations
 
+import json
+from typing import Any
+
+import pandas as pd
+import streamlit as st
+from dotenv import load_dotenv
+
+from services.openai_service import OpenAIRecommender
+from services.spotify_service import SpotifyRecommender
+from utils.prompt_templates import USER_INPUT_GUIDE
+
+load_dotenv()
+
+APP_TITLE = "🎵 음악 플리 추천"
+GENRES = ["K-POP", "POP", "HIPHOP", "R&B", "JAZZ", "CLASSICAL", "LOFI", "EDM", "INDIE"]
+TONES = ["밝음", "차분함", "몽환적", "집중", "신나는", "감성적"]
+
+
+def get_secret(key: str) -> str:
+    """st.secrets 우선, 없으면 환경변수로 fallback."""
+    if key in st.secrets:
+        return str(st.secrets[key])
+    return st.secrets.get("env", {}).get(key, "") if "env" in st.secrets else ""
+
+
+def get_env_or_secret(key: str) -> str:
+    value = get_secret(key)
+    if value:
+        return value
+    import os
+
+    return os.getenv(key, "")
+
+
+def init_session_state() -> None:
+    defaults = {
+        "model": "gpt-4o-mini",
+        "track_count": 12,
+        "market": "KR",
+        "allow_explicit": False,
+        "mood": "",
+        "activity": "",
+        "selected_genres": ["K-POP", "POP"],
+        "energy": 5,
+        "tone": "차분함",
+        "result": None,
+    }
+    for key, value in defaults.items():
+        if key not in st.session_state:
+            st.session_state[key] = value
+
+
+def reset_settings() -> None:
+    for key in ["model", "track_count", "market", "allow_explicit"]:
+        st.session_state.pop(key, None)
+    init_session_state()
+
+
+def validate_keys() -> dict[str, str]:
+    keys = {
+        "OPENAI_API_KEY": get_env_or_secret("OPENAI_API_KEY"),
+        "SPOTIFY_CLIENT_ID": get_env_or_secret("SPOTIFY_CLIENT_ID"),
+        "SPOTIFY_CLIENT_SECRET": get_env_or_secret("SPOTIFY_CLIENT_SECRET"),
+    }
+    return keys
+
+
+def render_result(result: dict[str, Any]) -> None:
+    analysis = result["analysis"]
+    tracks = result["tracks"]
+
+    with st.container(border=True):
+        st.subheader("AI 해석 결과")
+        st.markdown(f"- **mood_summary:** {analysis['mood_summary']}")
+        st.markdown(f"- **keywords:** {', '.join(analysis['keywords'])}")
+        st.markdown(f"- **playlist_theme:** {analysis['playlist_theme']}")
+        st.markdown(f"- **reason:** {analysis['reason']}")
+
+    st.subheader("추천 곡")
+    table_rows = []
+    for idx, track in enumerate(tracks, start=1):
+        preview_url = track.get("preview_url") or "미리듣기 없음"
+        table_rows.append(
+            {
+                "순번": idx,
+                "곡명": track.get("name"),
+                "아티스트": ", ".join(track.get("artists", [])),
+                "앨범": track.get("album"),
+                "preview_url": preview_url,
+                "spotify_url": track.get("spotify_url"),
+            }
+        )
+
+    df = pd.DataFrame(table_rows)
+    st.dataframe(df, use_container_width=True)
+
+    output_payload = {
+        "analysis": analysis,
+        "tracks": tracks,
+    }
+    st.download_button(
+        "결과 JSON 다운로드",
+        data=json.dumps(output_payload, ensure_ascii=False, indent=2),
+        file_name="playlist_recommendation.json",
+        mime="application/json",
+    )
+
+
+def main() -> None:
+    st.set_page_config(page_title="음악 플리 추천", page_icon="🎵", layout="wide")
+    init_session_state()
+
+    st.title(APP_TITLE)
+    st.caption("기분/상황 기반 AI+Spotify 추천")
+
+    st.sidebar.header("설정")
+    st.sidebar.selectbox("OpenAI 모델", ["gpt-4o-mini", "gpt-4.1-mini"], key="model")
+    st.sidebar.slider("추천 곡 수", 5, 30, key="track_count")
+    st.sidebar.selectbox("시장 코드", ["KR", "US", "JP"], key="market")
+    st.sidebar.checkbox("Explicit 허용", key="allow_explicit")
+    st.sidebar.button("설정 초기화", on_click=reset_settings)
+
+    with st.form("recommend_form"):
+        st.text_input("오늘의 기분", key="mood", placeholder="예: 살짝 우울하지만 힘내고 싶어요")
+        st.text_input("현재 상황/활동", key="activity", placeholder="예: 퇴근 후 산책")
+        st.multiselect("선호 장르", GENRES, key="selected_genres")
+        st.slider("에너지 레벨", 1, 10, key="energy")
+        st.selectbox("감정 톤", TONES, key="tone")
+        submitted = st.form_submit_button("플리 추천 받기", type="primary")
+
+    api_keys = validate_keys()
+    missing = [k for k, v in api_keys.items() if not v]
+    if missing:
+        st.warning(f"필수 API 키가 없습니다: {', '.join(missing)}. .env 또는 Streamlit secrets를 설정해주세요.")
+
+    if submitted and not missing:
+        user_input = {
+            "mood": st.session_state["mood"],
+            "activity": st.session_state["activity"],
+            "genres": st.session_state["selected_genres"],
+            "energy": st.session_state["energy"],
+            "tone": st.session_state["tone"],
+        }
+
+        if not user_input["mood"] or not user_input["activity"]:
+            st.error("기분과 상황/활동을 입력해주세요.")
+        else:
+            with st.spinner("AI가 분위기를 분석하고 Spotify에서 곡을 찾는 중입니다..."):
+                openai_client = OpenAIRecommender(api_key=api_keys["OPENAI_API_KEY"], model=st.session_state["model"])
+                spotify_client = SpotifyRecommender(
+                    client_id=api_keys["SPOTIFY_CLIENT_ID"],
+                    client_secret=api_keys["SPOTIFY_CLIENT_SECRET"],
+                )
+                analysis = openai_client.build_playlist_strategy(user_input)
+                tracks = spotify_client.find_tracks(
+                    strategy=analysis,
+                    track_count=st.session_state["track_count"],
+                    market=st.session_state["market"],
+                    allow_explicit=st.session_state["allow_explicit"],
+                )
+                st.session_state["result"] = {"analysis": analysis, "tracks": tracks}
+
+    if st.session_state.get("result"):
+        render_result(st.session_state["result"])
+
+    with st.expander("입력 가이드"):
+        st.markdown(USER_INPUT_GUIDE)
+
+
+if __name__ == "__main__":
+    main()
 
EOF
)
