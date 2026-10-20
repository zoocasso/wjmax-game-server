# WJMAX game server

[![tests](https://github.com/zoocasso/wjmax-game-server/actions/workflows/ci.yml/badge.svg)](https://github.com/zoocasso/wjmax-game-server/actions/workflows/ci.yml)

[English](#english) · [한국어](#한국어)

## English

The play-log ingestion API of **WJMAX**, a fan-made rhythm game in the Woowakgood community. Side project, Aug 2023 – Feb 2024, two people: the main developer built the game and I was the sole server developer (server, security layer, database). About 300 players were online on average and about 2,000 at the peak of an update day.

In production: **game client → Cloudflare (proxy, WAF) → AWS EC2 (FastAPI in Docker) → AWS RDS (MySQL)**.

This repository holds the service's API, cleaned up and rewritten in October 2026. The request the game client sends is unchanged.

### Design

- **One transaction per request.** A report is stored completely or not at all; malformed input is rejected with `422` before anything is written.
- **Devices are registered once.** The first report creates the device (`INSERT IGNORE`) and later reports keep its first-seen time.
- **One lookup per report.** The first chart key of every song in a report comes from a single grouped query.
- **Validated input.** `count_log` is read as JSON or a Python literal; each entry must be a title and eight non-negative integers. Songs that are not in `music_tb` are skipped and returned in `unknown_titles`.
- **Starts without the database.** Tables are declared in code ([`schema.sql`](schema.sql) has the DDL), the engine is created on first use, and stale connections are checked before use. `GET /healthz` reports database trouble as `503`.
- **No secrets in the image.** Settings come from the environment at run time, the container runs as a non-root user, and the API docs are off unless `ENABLE_DOCS=1`.
- **Tested.** [`tests/`](tests/) covers parsing and the API on SQLite; GitHub Actions runs them on every push.

### API

`POST /insert_playcount`, as the game client sends it:

```json
{"device_id": "…", "count_log": "{'playDatas': ['Oort Cloud*3*1*0*0*2*0*0*0']}"}
```

Each entry is a song title and the play count of each of its eight charts. The response is `{"saved": 8, "unknown_titles": []}`.

### Run

```bash
cp .env.example .env              # set DATABASE_URL
mysql wjmax_db < schema.sql
pip install -r requirements.txt
uvicorn app.main:app --reload
python client.py                  # sends one report
```

With Docker: `docker build -t wjmax-server .` and `docker run --env-file .env -p 8000:8000 wjmax-server`.

Tests: `pip install -r requirements-dev.txt` and `python -m pytest -q`.

## 한국어

우왁굳 팬게임 **왁제이맥스(WJMAX)**의 플레이 로그 수집 API입니다. 사이드 프로젝트(2023.08 ~ 2024.02, 2인 팀)로, 게임은 메인 개발자가 만들고 저는 서버를 단독으로 맡아 서버·보안 계층·데이터베이스를 담당했습니다. 동시 접속은 평균 약 300명, 업데이트 날 최대 약 2,000명이었습니다.

운영 구성: **게임 클라이언트 → Cloudflare(프록시, WAF) → AWS EC2(Docker의 FastAPI) → AWS RDS(MySQL)**.

이 저장소는 서비스 API를 2026년 10월에 정리해 다시 쓴 것입니다. 게임 클라이언트가 보내는 요청은 그대로입니다.

- **요청 하나에 트랜잭션 하나**: 보고 하나는 전부 저장되거나 전혀 저장되지 않습니다. 잘못된 입력은 아무것도 쓰기 전에 `422`로 거절합니다.
- **기기는 한 번만 등록**: 첫 보고에서 기기를 만들고(`INSERT IGNORE`), 이후 보고는 처음 본 시각을 유지합니다.
- **조회는 보고당 한 번**: 보고에 담긴 모든 곡의 첫 차트 키를 그룹 쿼리 하나로 가져옵니다.
- **입력 검증**: 각 항목은 곡 제목과 0 이상의 정수 8개여야 합니다. `music_tb`에 없는 곡은 건너뛰고 `unknown_titles`로 돌려줍니다.
- **DB 없이도 시작**: 테이블은 코드와 [`schema.sql`](schema.sql)에 선언하고, 엔진은 처음 쓸 때 만들며, 오래된 연결은 쓰기 전에 확인합니다. `GET /healthz`는 DB 문제를 `503`으로 알립니다.
- **이미지에 비밀값 없음**: 설정은 실행할 때 환경 변수로 받고, 컨테이너는 root가 아닌 사용자로 돌며, API 문서는 `ENABLE_DOCS=1`일 때만 엽니다.
- **테스트**: [`tests/`](tests/)의 파싱·API 테스트를 GitHub Actions가 push마다 돌립니다.

실행 방법은 위의 [Run](#run)과 같습니다.
