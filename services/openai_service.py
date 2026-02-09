from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI


@dataclass(frozen=True)
class StrategyResult:
    mood_summary: str
    keywords: List[str]
    seed_genres: List[str]
    search_queries: List[str]
    playlist_theme: str
    reason: str


class OpenAIService:
    """
    - 응답은 JSON only를 강제
    - JSON 파싱 실패 시 1~2회 재시도
    - 민감정보(키) 로그 출력 금지
    """

    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(api_key=api_key)

    def generate_strategy_json(
        self,
        model: str,
        prompt: str,
        max_retries: int = 2,
        timeout_s: int = 45,
    ) -> StrategyResult:
        last_err: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                # Responses API: JSON mode -> text.format: {"type":"json_object"}  :contentReference[oaicite:0]{index=0}
                resp = self._client.responses.create(
                    model=model,
                    input=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that ONLY outputs valid JSON objects.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    text={"format": {"type": "json_object"}},
                    timeout=timeout_s,
                )

                text_out = resp.output_text
                data = json.loads(text_out)

                return StrategyResult(
                    mood_summary=str(data["mood_summary"]),
                    keywords=list(data["keywords"]),
                    seed_genres=list(data["seed_genres"]),
                    search_queries=list(data["search_queries"]),
                    playlist_theme=str(data["playlist_theme"]),
                    reason=str(data["reason"]),
                )
            except Exception as e:
                last_err = e
                # 짧은 backoff
                time.sleep(0.6 * (attempt + 1))

        # 여기까지 오면 실패
        assert last_err is not None
        raise last_err
