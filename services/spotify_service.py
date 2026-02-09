from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

import requests


@dataclass(frozen=True)
class TrackRow:
    track_id: str
    track_name: str
    artist_name: str
    album_name: str
    preview_url: str
    spotify_url: str
    explicit: bool

    def to_dict(self) -> Dict[str, str]:
        return {
            "track_id": self.track_id,
            "track_name": self.track_name,
            "artist_name": self.artist_name,
            "album_name": self.album_name,
            "preview_url": self.preview_url,
            "spotify_url": self.spotify_url,
            "explicit": str(self.explicit),
        }


class SpotifyService:
    """
    Client Credentials Flow 기반:
    - 토큰은 1시간 유효, 캐시하여 재사용
    - market 파라미터 적용
    - 결과 병합 + 중복 제거
    - 결과 부족 시 대체 쿼리 재검색
    """

    TOKEN_URL = "https://accounts.spotify.com/api/token"
    SEARCH_URL = "https://api.spotify.com/v1/search"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expire_at: float = 0.0

    def _get_access_token(self) -> str:
        now = time.time()
        if self._token and now < (self._token_expire_at - 30):
            return self._token

        # Client Credentials Flow  :contentReference[oaicite:1]{index=1}
        basic = f"{self._client_id}:{self._client_secret}".encode("utf-8")
        auth = base64.b64encode(basic).decode("utf-8")

        resp = requests.post(
            self.TOKEN_URL,
            headers={"Authorization": f"Basic {auth}"},
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        self._token = data["access_token"]
        self._token_expire_at = now + int(data.get("expires_in", 3600))
        return self._token

    def _search_once(
        self,
        q: str,
        market: str,
        limit: int = 50,
    ) -> List[TrackRow]:
        token = self._get_access_token()
        resp = requests.get(
            self.SEARCH_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "q": q,
                "type": "track",
                "market": market,
                "limit": limit,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        items = (data.get("tracks") or {}).get("items") or []

        rows: List[TrackRow] = []
        for it in items:
            track_id = it.get("id") or ""
            name = it.get("name") or ""
            artists = it.get("artists") or []
            artist_name = artists[0].get("name") if artists else ""
            album = it.get("album") or {}
            album_name = album.get("name") or ""
            preview_url = it.get("preview_url") or "미리듣기 없음"
            spotify_url = ((it.get("external_urls") or {}).get("spotify")) or ""
            explicit = bool(it.get("explicit", False))

            if track_id and spotify_url:
                rows.append(
                    TrackRow(
                        track_id=track_id,
                        track_name=name,
                        artist_name=artist_name,
                        album_name=album_name,
                        preview_url=preview_url,
                        spotify_url=spotify_url,
                        explicit=explicit,
                    )
                )
        return rows

    @staticmethod
    def _dedupe_keep_order(rows: Iterable[TrackRow]) -> List[TrackRow]:
        seen: Set[str] = set()
        out: List[TrackRow] = []
        for r in rows:
            if r.track_id in seen:
                continue
            seen.add(r.track_id)
            out.append(r)
        return out

    def search_tracks_from_strategy(
        self,
        strategy: object,
        market: str,
        target_count: int,
        allow_explicit: bool,
    ) -> List[TrackRow]:
        # StrategyResult duck-typing
        search_queries: List[str] = list(getattr(strategy, "search_queries"))
        keywords: List[str] = list(getattr(strategy, "keywords"))
        seed_genres: List[str] = list(getattr(strategy, "seed_genres"))

        # 1) 1차 검색 (전략 쿼리 기반)
        merged: List[TrackRow] = []
        for q in search_queries:
            merged.extend(self._search_once(q=q, market=market, limit=50))
            if len(merged) >= target_count * 3:
                break

        # 2) 결과 부족 시: 대체 쿼리 자동 생성 (키워드/장르 조합)
        if len(self._dedupe_keep_order(merged)) < target_count:
            fallbacks = self._build_fallback_queries(keywords=keywords, seed_genres=seed_genres)
            for q in fallbacks:
                merged.extend(self._search_once(q=q, market=market, limit=50))
                if len(self._dedupe_keep_order(merged)) >= target_count:
                    break

        # 3) 중복 제거
        merged = self._dedupe_keep_order(merged)

        # 4) explicit 필터링
        if not allow_explicit:
            merged = [r for r in merged if not r.explicit]

        # 5) target_count로 컷
        return merged[:target_count]

    @staticmethod
    def _build_fallback_queries(keywords: List[str], seed_genres: List[str]) -> List[str]:
        kws = [k.strip() for k in keywords if k.strip()]
        gens = [g.strip() for g in seed_genres if g.strip()]

        out: List[str] = []
        # 최대한 과도한 쿼리 폭발 방지
        for g in gens[:3]:
            out.append(f'genre:"{g}"')
        for k in kws[:5]:
            out.append(f'"{k}"')
        # 혼합
        for g in gens[:2]:
            for k in kws[:3]:
                out.append(f'{k} {g}')
        # 마지막 광역
        out.append("top hits")
        return out
