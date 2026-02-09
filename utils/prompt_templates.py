 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/utils/prompt_templates.py b/utils/prompt_templates.py
new file mode 100644
index 0000000000000000000000000000000000000000..17875065eeeca3a38476d89f88fb15467bc010b6
--- /dev/null
+++ b/utils/prompt_templates.py
@@ -0,0 +1,41 @@
+from __future__ import annotations
+
+from typing import Any
+
+
+USER_INPUT_GUIDE = """
+- **기분**: 지금 느끼는 감정을 자유롭게 입력하세요.
+- **상황/활동**: 공부, 운동, 퇴근길 등 현재 맥락을 적어주세요.
+- **장르/에너지/톤**: 원하는 분위기에 가까울수록 추천 정확도가 높아집니다.
+"""
+
+
+def build_system_prompt() -> str:
+    return (
+        "너는 음악 추천 전략가다. 한국어 사용자 입력을 해석해 Spotify 검색 전략을 JSON으로 반환하라. "
+        "반드시 JSON만 출력하고, 마크다운/코드블록을 포함하지 마라. "
+        "장르 편향을 피하고 다양한 트랙이 나오도록 seed_genres와 search_queries를 구성하라."
+    )
+
+
+def build_user_prompt(user_input: dict[str, Any]) -> str:
+    return f"""
+다음 사용자 입력을 기반으로 플레이리스트 추천 전략을 만들어라.
+
+입력:
+- mood: {user_input.get('mood')}
+- activity: {user_input.get('activity')}
+- genres: {user_input.get('genres')}
+- energy(1-10): {user_input.get('energy')}
+- tone: {user_input.get('tone')}
+
+반드시 아래 JSON 스키마를 지켜라:
+{{
+  "mood_summary": "string",
+  "keywords": ["string", "string", "string"],
+  "seed_genres": ["spotify genre token"],
+  "search_queries": ["spotify search query"],
+  "playlist_theme": "string",
+  "reason": "string"
+}}
+""".strip()
 
EOF
)
