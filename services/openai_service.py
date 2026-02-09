 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/services/openai_service.py b/services/openai_service.py
new file mode 100644
index 0000000000000000000000000000000000000000..5e9a0d7de067b1fc08f513a00b932fda99b1cae4
--- /dev/null
+++ b/services/openai_service.py
@@ -0,0 +1,47 @@
+from __future__ import annotations
+
+import json
+from typing import Any
+
+from openai import OpenAI
+
+from utils.prompt_templates import build_system_prompt, build_user_prompt
+
+
+class OpenAIRecommender:
+    def __init__(self, api_key: str, model: str) -> None:
+        self.client = OpenAI(api_key=api_key)
+        self.model = model
+
+    def build_playlist_strategy(self, user_input: dict[str, Any]) -> dict[str, Any]:
+        """JSON 파싱 실패 시 재시도(최대 3회)하여 전략 생성."""
+        system_prompt = build_system_prompt()
+        user_prompt = build_user_prompt(user_input)
+
+        for attempt in range(3):
+            response = self.client.chat.completions.create(
+                model=self.model,
+                temperature=0.4,
+                response_format={"type": "json_object"},
+                messages=[
+                    {"role": "system", "content": system_prompt},
+                    {"role": "user", "content": user_prompt},
+                ],
+            )
+            content = response.choices[0].message.content or "{}"
+            try:
+                parsed = json.loads(content)
+                self._validate(parsed)
+                return parsed
+            except (json.JSONDecodeError, ValueError):
+                if attempt == 2:
+                    raise ValueError("OpenAI 응답을 JSON으로 파싱하지 못했습니다.")
+
+        raise ValueError("OpenAI 전략 생성에 실패했습니다.")
+
+    @staticmethod
+    def _validate(payload: dict[str, Any]) -> None:
+        required = ["mood_summary", "keywords", "seed_genres", "search_queries", "playlist_theme", "reason"]
+        for key in required:
+            if key not in payload:
+                raise ValueError(f"누락된 필드: {key}")
 
EOF
)
