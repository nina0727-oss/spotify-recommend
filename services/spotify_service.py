 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/services/spotify_service.py b/services/spotify_service.py
new file mode 100644
index 0000000000000000000000000000000000000000..52c13479a7c949428842ce9db11dbd88ddfde76e
--- /dev/null
+++ b/services/spotify_service.py
@@ -0,0 +1,63 @@
+from __future__ import annotations
+
+from typing import Any
+
+import spotipy
+from spotipy.oauth2 import SpotifyClientCredentials
+
+
+class SpotifyRecommender:
+    def __init__(self, client_id: str, client_secret: str) -> None:
+        auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
+        self.client = spotipy.Spotify(auth_manager=auth_manager, requests_timeout=10, retries=2)
+
+    def find_tracks(
+        self,
+        strategy: dict[str, Any],
+        track_count: int,
+        market: str,
+        allow_explicit: bool,
+    ) -> list[dict[str, Any]]:
+        queries = list(strategy.get("search_queries", []))
+        genres = list(strategy.get("seed_genres", []))
+
+        # 검색 결과가 부족할 때를 대비한 대체 쿼리
+        fallback_queries = [f"genre:{g}" for g in genres if g]
+        all_queries = [q for q in queries + fallback_queries if q]
+
+        seen_ids: set[str] = set()
+        collected: list[dict[str, Any]] = []
+
+        for query in all_queries:
+            try:
+                response = self.client.search(q=query, type="track", limit=20, market=market)
+            except spotipy.SpotifyException as exc:
+                raise RuntimeError(f"Spotify API 호출 실패: {exc}") from exc
+
+            items = response.get("tracks", {}).get("items", [])
+            for item in items:
+                track_id = item.get("id")
+                if not track_id or track_id in seen_ids:
+                    continue
+                if (not allow_explicit) and item.get("explicit"):
+                    continue
+
+                seen_ids.add(track_id)
+                collected.append(
+                    {
+                        "id": track_id,
+                        "name": item.get("name", ""),
+                        "artists": [artist.get("name", "") for artist in item.get("artists", [])],
+                        "album": item.get("album", {}).get("name", ""),
+                        "preview_url": item.get("preview_url"),
+                        "spotify_url": item.get("external_urls", {}).get("spotify", ""),
+                        "popularity": item.get("popularity", 0),
+                    }
+                )
+
+            if len(collected) >= track_count * 2:
+                break
+
+        # 인기도 기반 정렬 후 N개 반환
+        collected.sort(key=lambda x: x.get("popularity", 0), reverse=True)
+        return collected[:track_count]
 
EOF
)
