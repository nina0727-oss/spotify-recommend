# 🎵 음악 플리 추천 (Streamlit Cloud 배포용)

기분/상황/장르/에너지/톤 입력을 바탕으로  
OpenAI가 **추천 전략(JSON)** 을 만들고, Spotify에서 실제 트랙을 검색해 플레이리스트를 보여주는 앱입니다.

## 1) 기능
- 사용자 입력 수집
- OpenAI API로 전략 JSON 생성 (JSON only, 파싱 실패 시 재시도)
- Spotify API(Client Credentials Flow)로 트랙 검색
- 결과 렌더링(카드 + 테이블)
- 전략 JSON 다운로드
- session_state 유지

## 2) 필수 Secrets 키
아래 3개가 반드시 필요합니다.
- `OPENAI_API_KEY`
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`

앱은 **st.secrets 우선**, 없으면 **.env fallback** 으로 동일하게 동작합니다.

## 3) 로컬 실행
### (1) 설치
```bash
python -m venv .venv
# mac/linux
source .venv/bin/activate
# windows
# .venv\Scripts\activate

pip install -r requirements.txt
