# Economic RSS Monitor

FastAPI 단일 서비스로 동작하는 경제 RSS/공식 페이지 모니터입니다.

## Stack

- FastAPI
- Jinja2
- HTMX
- APScheduler
- feedparser
- SQLAlchemy
- SQLite for local development
- PostgreSQL for Railway

## Sources

### 국내 경제

- 한국 경제: https://www.hankyung.com/feed/economy
- 매일 경제: https://www.mk.co.kr/rss/30100041/

### 해외 경제

- Press Releases
- Monetary Policy
- Speeches and Testimony
- FEDS Notes
- Selected Interest Rates
- Foreign Exchange Rates

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000.

## API

```text
GET  /api/articles
GET  /api/articles?section=domestic
GET  /api/articles?section=global
GET  /api/articles?source=hankyung
POST /api/fetch-now
```

## Railway

1. Create a Railway PostgreSQL database.
2. Set `DATABASE_URL` from Railway PostgreSQL.
3. Deploy this service.

Railway start command is configured in `railway.json`.

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

The app uses one worker because APScheduler runs inside the FastAPI process.
